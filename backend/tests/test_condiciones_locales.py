"""Pruebas de las condiciones locales de Clima: ventana para labores, lectura de Open-Meteo y la ruta /api/clima/local (sin red)."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Antes de importar la app: así la base apunta a una carpeta temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import condiciones_locales as cl  # noqa: E402
from app.services import clima as clima_servicio  # noqa: E402
from app.services import openmeteo  # noqa: E402
from app.services.ubicaciones import Ubicacion  # noqa: E402

lugar = Ubicacion(1, "Monterrey, NL", 25.6866, -100.3161, "America/Monterrey", cve_ent="19")


def horas(buenas_desde: int, buenas_hasta: int):
    """24 horas del día: sirven para el campo las de buenas_desde a buenas_hasta (sin incluir la última)."""
    return [
        {
            "hora": h,
            "temperatura": 24,
            "vientoKmh": 10 if buenas_desde <= h < buenas_hasta else 40,
            "lluvia": 5,
        }
        for h in range(24)
    ]


def respuesta(hora_actual: int = 10):
    tiempos = [f"2026-11-15T{h:02d}:00" for h in range(24)]
    return {
        "current": {
            "time": f"2026-11-15T{hora_actual:02d}:15",
            "temperature_2m": 30.4,
            "apparent_temperature": 31.2,
            "relative_humidity_2m": 48.0,
            "wind_speed_10m": 12.3,
            "wind_direction_10m": 50,
            "weather_code": 0,
        },
        "hourly": {
            "time": tiempos,
            "temperature_2m": [24.0] * 24,
            "wind_speed_10m": [10.0 if h < 17 else 30.0 for h in range(24)],
            "precipitation_probability": [8] * 24,
            "soil_temperature_18cm": [23.6] * 24,
        },
        "daily": {
            "temperature_2m_max": [31.4],
            "temperature_2m_min": [17.6],
            "precipitation_sum": [0.24],
            "precipitation_probability_max": [8],
        },
    }


def compartido(optimo=True):
    """Lo que devuelve el clima de Principal (Meteomatics): cifras distintas a las de Open-Meteo a propósito."""
    return {
        "municipio": "Monterrey, NL",
        "fuente": "Meteomatics",
        "pronostico": [{"fecha": "2026-11-15", "tmax": 27, "tmin": 15, "lluvia": 78, "cielo": "lluvia"}],
        "hoy": {
            "temperatura": 20, "sensacion": 26, "cielo": "Mostly clear", "icono": "sol", "optimoParaCampo": optimo,
            "humedad": 82, "vientoKmh": 2, "humedadSuelo": 42, "phSuelo": 7.6,
        },
    }


class PruebasVentana(unittest.TestCase):
    def test_favorable_hasta_la_primera_hora_que_no_sirve(self):
        v = cl.ventana(horas(0, 17), 10)
        self.assertEqual(v, {"favorable": True, "desde": None, "hasta": "17:00"})

    def test_favorable_todo_el_dia(self):
        v = cl.ventana(horas(0, 24), 10)
        self.assertTrue(v["favorable"])
        self.assertIsNone(v["hasta"])

    def test_no_favorable_avisa_cuando_empieza_la_siguiente(self):
        v = cl.ventana(horas(14, 18), 10)
        self.assertEqual(v, {"favorable": False, "desde": "14:00", "hasta": None})

    def test_sin_horas_buenas_no_hay_ventana(self):
        v = cl.ventana(horas(0, 8), 10)  # las buenas ya pasaron
        self.assertFalse(v["favorable"])
        self.assertIsNone(v["desde"])

    def test_sin_dato_no_se_da_por_buena(self):
        self.assertFalse(cl._sirve(None, 10, 5))
        self.assertFalse(cl._sirve(24, 10, None))
        self.assertTrue(cl._sirve(24, 10, 5))
        self.assertFalse(cl._sirve(36, 10, 5))  # demasiado caliente
        self.assertFalse(cl._sirve(24, 10, 30))  # lluvia probable

    def test_punto_cardinal(self):
        self.assertEqual(cl.punto_cardinal(0), "N")
        self.assertEqual(cl.punto_cardinal(50), "NE")
        self.assertEqual(cl.punto_cardinal(350), "N")
        self.assertEqual(cl.punto_cardinal(225), "SW")
        self.assertIsNone(cl.punto_cardinal(None))


class PruebasServicio(unittest.TestCase):
    def setUp(self):
        cl._cache.clear()

    def test_lee_las_condiciones_de_hoy(self):
        with patch.object(openmeteo, "_pedir", AsyncMock(return_value=respuesta())) as pedir:
            r = asyncio.run(cl.condiciones(lugar))
            asyncio.run(cl.condiciones(lugar))  # la segunda sale de la caché
        self.assertEqual(pedir.await_count, 1)
        self.assertEqual(r["temperatura"], 30)
        self.assertEqual(r["sensacion"], 31)
        self.assertEqual(r["vientoDireccion"], "NE")
        self.assertEqual(r["lluviaProbabilidad"], 8)
        self.assertEqual(r["lluviaMm"], 0.2)
        self.assertEqual(r["temperaturaSuelo"], 24)
        self.assertEqual((r["tmax"], r["tmin"]), (31, 18))
        self.assertEqual(r["ventana"], {"favorable": True, "desde": None, "hasta": "17:00"})

    def test_respuesta_rara_es_un_error_claro(self):
        with patch.object(openmeteo, "_pedir", AsyncMock(return_value={"current": {}})):
            with self.assertRaises(openmeteo.OpenMeteoError):
                asyncio.run(cl.condiciones(lugar))


class PruebasUnir(unittest.TestCase):
    def extras(self):
        cl._cache.clear()
        with patch.object(openmeteo, "_pedir", AsyncMock(return_value=respuesta())):
            return asyncio.run(cl.condiciones(lugar))

    def test_las_cifras_basicas_son_las_de_principal(self):
        r = cl.unir(compartido(), self.extras())
        # Open-Meteo diría 30° ahora y 31/18 de máxima/mínima: se usa lo mismo que Principal
        self.assertEqual((r["temperatura"], r["sensacion"], r["humedad"], r["vientoKmh"]), (20, 26, 82, 2))
        self.assertEqual((r["tmax"], r["tmin"], r["lluviaProbabilidad"]), (27, 15, 78))
        self.assertEqual(r["fuente"], "Meteomatics + Open-Meteo")

    def test_los_extras_vienen_de_open_meteo(self):
        r = cl.unir(compartido(), self.extras())
        self.assertEqual((r["vientoDireccion"], r["lluviaMm"], r["temperaturaSuelo"]), ("NE", 0.2, 24))

    def test_si_principal_dijo_que_no_es_buen_dia_la_ventana_no_lo_contradice(self):
        r = cl.unir(compartido(optimo=False), self.extras())
        self.assertEqual(r["ventana"], {"favorable": False, "desde": None, "hasta": None})
        r = cl.unir(compartido(optimo=True), self.extras())
        self.assertTrue(r["ventana"]["favorable"])

    def test_sin_extras_se_muestra_lo_de_principal(self):
        r = cl.unir(compartido(), None)
        self.assertEqual(r["temperatura"], 20)
        self.assertIsNone(r["ventana"])
        self.assertIsNone(r["vientoDireccion"])
        self.assertEqual(r["fuente"], "Meteomatics")

    def test_sin_principal_se_muestra_lo_de_open_meteo(self):
        r = cl.unir(None, self.extras())
        self.assertEqual((r["temperatura"], r["tmax"], r["tmin"]), (30, 31, 18))
        self.assertEqual(r["fuente"], "Open-Meteo")

    def test_si_las_dos_fuentes_son_open_meteo_no_se_repite(self):
        c = compartido()
        c["fuente"] = "Open-Meteo"
        self.assertEqual(cl.unir(c, self.extras())["fuente"], "Open-Meteo")

    def test_sin_nada_no_hay_resultado(self):
        self.assertIsNone(cl.unir(None, None))


RUTA = {"municipio": "Monterrey, NL"}
CLIMA = "app.routers.clima.clima_servicio.clima"
HUMEDAD = "app.routers.clima.suelo_ubicacion.humedad_raiz"


class PruebasRuta(unittest.TestCase):
    def setUp(self):
        cl._cache.clear()

    def test_ruta_local_usa_las_mismas_cifras_que_principal_y_suma_el_suelo(self):
        with TestClient(app) as cliente, patch.object(openmeteo, "_pedir", AsyncMock(return_value=respuesta())), patch(
            CLIMA, AsyncMock(return_value=compartido())
        ), patch(HUMEDAD, AsyncMock(return_value=61.6)):
            r = cliente.get("/api/clima/local", params=RUTA)
        self.assertEqual(r.status_code, 200)
        c = r.json()
        self.assertEqual((c["temperatura"], c["tmax"], c["tmin"]), (20, 27, 15))
        self.assertEqual(c["humedadSuelo"], 62)
        self.assertEqual(c["vientoDireccion"], "NE")

    def test_ruta_local_sin_humedad_del_suelo_responde_igual(self):
        with TestClient(app) as cliente, patch.object(openmeteo, "_pedir", AsyncMock(return_value=respuesta())), patch(
            CLIMA, AsyncMock(return_value=compartido())
        ), patch(HUMEDAD, AsyncMock(return_value=None)):
            r = cliente.get("/api/clima/local", params=RUTA)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["humedadSuelo"])

    def test_ruta_local_ubicacion_desconocida_es_404(self):
        with TestClient(app) as cliente:
            r = cliente.get("/api/clima/local", params={"municipio": "No existe"})
        self.assertEqual(r.status_code, 404)

    def test_ruta_local_si_falla_open_meteo_muestra_lo_de_principal(self):
        falla = AsyncMock(side_effect=openmeteo.OpenMeteoError("Could not get the forecast"))
        with TestClient(app) as cliente, patch.object(openmeteo, "_pedir", falla), patch(
            CLIMA, AsyncMock(return_value=compartido())
        ), patch(HUMEDAD, AsyncMock(return_value=None)):
            r = cliente.get("/api/clima/local", params=RUTA)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["temperatura"], 20)
        self.assertIsNone(r.json()["ventana"])

    def test_ruta_local_502_si_no_responde_ninguna_fuente(self):
        falla = AsyncMock(side_effect=openmeteo.OpenMeteoError("Could not get the forecast"))
        sin_clima = AsyncMock(side_effect=clima_servicio.ClimaNoDisponible("sin clima"))
        with TestClient(app) as cliente, patch.object(openmeteo, "_pedir", falla), patch(CLIMA, sin_clima), patch(
            HUMEDAD, AsyncMock(return_value=None)
        ):
            r = cliente.get("/api/clima/local", params=RUTA)
        self.assertEqual(r.status_code, 502)


if __name__ == "__main__":
    unittest.main()
