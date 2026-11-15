"""Pruebas del mapa de Clima: la malla de México, la lectura de Open-Meteo y la ruta /api/clima/mapa (sin red)."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Antes de importar la app: así la base apunta a una carpeta temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import mapa_clima  # noqa: E402

FECHAS = [f"2026-11-{15 + i}" for i in range(7)]


def respuesta_falsa(cuantos: int):
    """Lo que contesta Open-Meteo: un objeto si es una coordenada y una lista si son varias."""
    punto = {
        "daily": {
            "time": FECHAS,
            "precipitation_sum": [0.0, 1.24, None, 12.0, 0.0, 0.0, 30.55],
            "temperature_2m_max": [28.04, 30.0, 31.0, 25.0, 24.0, 26.0, 27.0],
        }
    }
    return punto if cuantos == 1 else [punto] * cuantos


class RespuestaFalsa:
    def __init__(self, cuantos):
        self.cuantos = cuantos

    def raise_for_status(self):
        pass

    def json(self):
        return respuesta_falsa(self.cuantos)


class ClienteFalso:
    """Reemplaza a httpx.AsyncClient: contesta según cuántas coordenadas se pidieron y recuerda las peticiones."""

    peticiones: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params):
        ClienteFalso.peticiones.append(params)
        return RespuestaFalsa(len(params["latitude"].split(",")))


class PruebasMalla(unittest.TestCase):
    def test_contorno_distingue_dentro_y_fuera(self):
        self.assertTrue(mapa_clima._dentro(-99.13, 19.43))  # Ciudad de México
        self.assertTrue(mapa_clima._dentro(-100.31, 25.68))  # Monterrey
        self.assertTrue(mapa_clima._dentro(-89.6, 20.9))  # Mérida
        self.assertTrue(mapa_clima._dentro(-110.3, 24.1))  # La Paz, Baja California Sur
        self.assertFalse(mapa_clima._dentro(-95.0, 24.0))  # Golfo de México
        self.assertFalse(mapa_clima._dentro(-120.0, 25.0))  # Océano Pacífico
        self.assertFalse(mapa_clima._dentro(-98.0, 35.0))  # Estados Unidos
        self.assertFalse(mapa_clima._dentro(-90.0, 14.0))  # Guatemala / Pacífico

    def test_la_malla_cubre_el_pais_sin_pasarse_de_consultas(self):
        puntos = mapa_clima.malla()
        # Cada punto de la malla es una consulta de Open-Meteo: ni muy pocos (mapa vacío) ni cientos
        self.assertTrue(60 <= len(puntos) <= 200, len(puntos))
        self.assertTrue(all(mapa_clima._dentro(lon, lat) for lat, lon in puntos))
        self.assertEqual(len(puntos), len(set(puntos)))
        lats = [p[0] for p in puntos]
        lons = [p[1] for p in puntos]
        self.assertLess(min(lats), 19)  # hay puntos en el sur
        self.assertGreater(max(lats), 28)  # y en el norte
        self.assertLess(min(lons), -112)  # y en Baja California
        self.assertGreater(max(lons), -90)  # y en la península de Yucatán

    def test_la_caja_envuelve_el_contorno(self):
        c = mapa_clima.caja()
        self.assertLess(c["lonMin"], -117)
        self.assertGreater(c["lonMax"], -87)
        self.assertLess(c["latMin"], 15)
        self.assertGreater(c["latMax"], 32)


class PruebasMapa(unittest.TestCase):
    def setUp(self):
        mapa_clima._cache.clear()
        ClienteFalso.peticiones = []

    def test_lee_una_o_varias_coordenadas(self):
        uno = mapa_clima._leer(respuesta_falsa(1), 1)
        tres = mapa_clima._leer(respuesta_falsa(3), 3)
        self.assertEqual(len(uno), 1)
        self.assertEqual(len(tres), 3)
        self.assertEqual(uno[0]["lluviaMm"][:4], [0.0, 1.2, None, 12.0])  # redondea a un decimal y respeta los vacíos
        self.assertEqual(uno[0]["tmax"][0], 28.0)
        self.assertEqual(uno[0]["fechas"], FECHAS)
        with self.assertRaises(ValueError):
            mapa_clima._leer(respuesta_falsa(2), 3)  # Open-Meteo devolvió menos puntos de los pedidos

    def test_pide_la_malla_y_los_lugares_en_lotes(self):
        lugares = [("Monterrey, NL", 25.6866, -100.3161)]
        with patch.object(mapa_clima.httpx, "AsyncClient", ClienteFalso):
            r = asyncio.run(mapa_clima.mapa(lugares))
        n = len(mapa_clima.malla())
        self.assertEqual(len(r["puntos"]), n)
        self.assertEqual([lugar["nombre"] for lugar in r["lugares"]], ["Monterrey, NL"])
        self.assertEqual(r["dias"], FECHAS)
        self.assertEqual(r["lugares"][0]["tmax"][1], 30.0)
        self.assertEqual(r["fuente"], "Open-Meteo")
        self.assertFalse(r["desactualizado"])
        self.assertEqual(len(r["contorno"]), len(mapa_clima.CONTORNO))
        # Ningún lote pasa del máximo y entre todos llevan la malla y el lugar
        tamanos = [len(p["latitude"].split(",")) for p in ClienteFalso.peticiones]
        self.assertTrue(all(t <= mapa_clima.POR_CONSULTA for t in tamanos))
        self.assertEqual(sum(tamanos), n + 1)
        self.assertEqual(ClienteFalso.peticiones[0]["forecast_days"], 7)

    def test_la_cache_evita_volver_a_consultar(self):
        with patch.object(mapa_clima.httpx, "AsyncClient", ClienteFalso):
            asyncio.run(mapa_clima.mapa([]))
            consultas = len(ClienteFalso.peticiones)
            asyncio.run(mapa_clima.mapa([]))
        self.assertEqual(len(ClienteFalso.peticiones), consultas)

    def test_si_open_meteo_falla_usa_la_copia_vieja(self):
        with patch.object(mapa_clima.httpx, "AsyncClient", ClienteFalso):
            asyncio.run(mapa_clima.mapa([]))
        llave = next(iter(mapa_clima._cache))
        antes, datos = mapa_clima._cache[llave]
        mapa_clima._cache[llave] = (antes - mapa_clima.SEGUNDOS_CACHE - 1, datos)  # la caché venció
        falla = AsyncMock(side_effect=mapa_clima.ErrorMapaClima("sin red"))
        with patch.object(mapa_clima, "_pedir", falla):
            r = asyncio.run(mapa_clima.mapa([]))
        self.assertTrue(r["desactualizado"])
        self.assertEqual(len(r["puntos"]), len(datos["puntos"]))

    def test_sin_copia_vieja_el_error_sale(self):
        falla = AsyncMock(side_effect=mapa_clima.ErrorMapaClima("sin red"))
        with patch.object(mapa_clima, "_pedir", falla), self.assertRaises(mapa_clima.ErrorMapaClima):
            asyncio.run(mapa_clima.mapa([]))

    def test_si_un_punto_trae_menos_dias_se_recortan_todos(self):
        puntos = [
            {"fechas": FECHAS, "lluviaMm": [1.0] * 7, "tmax": [20.0] * 7},
            {"fechas": FECHAS[:5], "lluviaMm": [2.0] * 5, "tmax": [21.0] * 5},
        ]
        fechas = mapa_clima._fechas_comunes(puntos)
        self.assertEqual(len(fechas), 5)
        self.assertTrue(all(len(p["lluviaMm"]) == 5 and len(p["tmax"]) == 5 for p in puntos))


class PruebasRuta(unittest.TestCase):
    def setUp(self):
        mapa_clima._cache.clear()
        ClienteFalso.peticiones = []

    def test_ruta_mapa_incluye_los_lugares_guardados(self):
        with TestClient(app) as cliente, patch.object(mapa_clima.httpx, "AsyncClient", ClienteFalso):
            r = cliente.get("/api/clima/mapa")
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertTrue(len(cuerpo["puntos"]) > 50)
        self.assertTrue(len(cuerpo["lugares"]) >= 1)  # las ciudades de inicio de la base
        self.assertEqual(len(cuerpo["lugares"][0]["lluviaMm"]), 7)
        self.assertIn("lonMin", cuerpo["caja"])

    def test_ruta_mapa_responde_502_si_no_hay_datos(self):
        falla = AsyncMock(side_effect=mapa_clima.ErrorMapaClima("Could not get the map forecast"))
        with TestClient(app) as cliente, patch.object(mapa_clima, "_pedir", falla):
            r = cliente.get("/api/clima/mapa")
        self.assertEqual(r.status_code, 502)
        self.assertIn("map forecast", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
