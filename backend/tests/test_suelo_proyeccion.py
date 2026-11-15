"""Pruebas de la proyección del suelo a 7 días: el balance de agua, la calibración y la ruta /api/suelo/proyeccion (sin red)."""

import asyncio
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Antes de importar la app: así la base apunta a una carpeta temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.suelo import proyeccion as pr  # noqa: E402

HOY = date(2026, 11, 15)
PASADOS = 14


def fechas_om():
    """Los 14 días anteriores a hoy y hoy + 6, como los devuelve Open-Meteo."""
    return [(HOY + timedelta(days=i)).isoformat() for i in range(-PASADOS, 7)]


def respuesta_om(lluvia=0.0, et0=3.0, temp=20.0, lluvia_por_fecha=None):
    fechas = fechas_om()
    return {
        "daily": {
            "time": fechas,
            "precipitation_sum": [(lluvia_por_fecha or {}).get(f, lluvia) for f in fechas],
            "et0_fao_evapotranspiration": [et0] * len(fechas),
        },
        "hourly": {
            "time": [f"{f}T{h:02d}:00" for f in fechas for h in range(24)],
            "soil_temperature_0cm": [temp] * (24 * len(fechas)),
        },
    }


def real_power(humedad=40.0, ev=1.8, ts=22.0, hasta=date(2026, 11, 12), con_vacios=3):
    """14 días de POWER terminando en `hasta`, más días sin dato (-999 -> None) como pasa con el retraso."""
    filas = []
    for i in range(14, -1, -1):
        d = hasta - timedelta(days=i)
        filas.append({"fecha": d.strftime("%Y%m%d"), "humedad_raiz": humedad, "temperatura_suelo": ts, "evaporacion_mm_dia": ev})
    for i in range(1, con_vacios + 1):
        d = hasta + timedelta(days=i)
        filas.append({"fecha": d.strftime("%Y%m%d"), "humedad_raiz": None, "temperatura_suelo": None, "evaporacion_mm_dia": None})
    return filas


class PruebasBalance(unittest.TestCase):
    def test_empieza_despues_del_ultimo_dato_real_y_llega_a_hoy_mas_seis(self):
        r = pr.proyectar(real_power(), respuesta_om())
        fechas = [f["fecha"] for f in r["proyeccion"]]
        self.assertEqual(r["ultimo_dato_real"], "2026-11-12")
        self.assertEqual(fechas[0], "2026-11-13")
        self.assertEqual(fechas[-1], "2026-11-21")
        self.assertEqual(r["hoy"], "2026-11-15")
        # Los días entre el último dato y hoy ya ocurrieron; de hoy en adelante es pronóstico
        self.assertEqual([f["pasado"] for f in r["proyeccion"][:4]], [True, True, False, False])

    def test_sin_lluvia_el_suelo_se_seca(self):
        r = pr.proyectar(real_power(), respuesta_om(lluvia=0.0))
        humedades = [f["humedad_raiz"] for f in r["proyeccion"]]
        self.assertTrue(all(b < a for a, b in zip(humedades, humedades[1:])))
        self.assertLess(r["resumen"]["cambio_pts"], 0)
        self.assertEqual(r["resumen"]["tendencia"], "baja")

    def test_la_lluvia_fuerte_lo_moja_y_se_avisa(self):
        om = respuesta_om(lluvia=0.0, lluvia_por_fecha={"2026-11-17": 45.0})
        r = pr.proyectar(real_power(), om)
        antes = next(f for f in r["proyeccion"] if f["fecha"] == "2026-11-16")["humedad_raiz"]
        despues = next(f for f in r["proyeccion"] if f["fecha"] == "2026-11-17")["humedad_raiz"]
        self.assertGreater(despues, antes + 5)  # 45 mm sobre ~450 mm de almacén son ~10 puntos
        self.assertEqual(r["resumen"]["lluvia_fuerte"], {"fecha": "2026-11-17", "mm": 45.0})

    def test_lluvia_moderada_no_se_marca_como_fuerte(self):
        r = pr.proyectar(real_power(), respuesta_om(lluvia=5.0))
        self.assertIsNone(r["resumen"]["lluvia_fuerte"])

    def test_nunca_pasa_de_100_ni_baja_del_minimo(self):
        mojado = pr.proyectar(real_power(humedad=99.0), respuesta_om(lluvia=80.0, et0=0.5))
        self.assertTrue(all(f["humedad_raiz"] <= 100 for f in mojado["proyeccion"]))
        seco = pr.proyectar(real_power(humedad=6.0), respuesta_om(lluvia=0.0, et0=9.0))
        self.assertTrue(all(f["humedad_raiz"] >= pr.MINIMO_PCT for f in seco["proyeccion"]))

    def test_calibra_la_perdida_con_la_evaporacion_real_del_punto(self):
        # POWER midió 1.5 mm/día y Open-Meteo da ET0 de 3.0: el factor es 0.5
        r = pr.proyectar(real_power(ev=1.5), respuesta_om(et0=3.0))
        self.assertEqual(r["supuestos"]["factor_evaporacion"], 0.5)
        self.assertEqual(r["proyeccion"][0]["evaporacion_mm_dia"], 1.5)

    def test_el_factor_se_limita_a_un_rango(self):
        r = pr.proyectar(real_power(ev=20.0), respuesta_om(et0=1.0))
        self.assertEqual(r["supuestos"]["factor_evaporacion"], pr.FACTOR_ET_MAX)

    def test_sin_evaporacion_real_usa_el_factor_por_defecto(self):
        real = real_power()
        for f in real:
            f["evaporacion_mm_dia"] = None
        r = pr.proyectar(real, respuesta_om())
        self.assertEqual(r["supuestos"]["factor_evaporacion"], pr.FACTOR_ET_DEFECTO)

    def test_la_temperatura_del_suelo_se_ajusta_a_la_de_power(self):
        # POWER dice 22 °C y Open-Meteo 20 °C los mismos días: la proyección se sube 2 °C para continuar la curva
        r = pr.proyectar(real_power(ts=22.0), respuesta_om(temp=20.0))
        self.assertEqual(r["supuestos"]["ajuste_temperatura_c"], 2.0)
        self.assertTrue(all(f["temperatura_suelo"] == 22.0 for f in r["proyeccion"]))
        self.assertEqual(r["resumen"]["temperatura_suelo_min"], 22.0)

    def test_totales_cuentan_solo_de_hoy_en_adelante(self):
        om = respuesta_om(lluvia=0.0, lluvia_por_fecha={"2026-11-13": 30.0, "2026-11-16": 4.0})
        r = pr.proyectar(real_power(), om)
        self.assertEqual(r["resumen"]["lluvia_total_mm"], 4.0)  # los 30 mm del 13 ya pasaron
        self.assertEqual(r["resumen"]["dias_con_lluvia"], 1)

    def test_no_modifica_lo_que_recibe(self):
        real = real_power()
        copia = [dict(f) for f in real]
        pr.proyectar(real, respuesta_om())
        self.assertEqual(real, copia)

    def test_sin_dato_real_es_un_error_claro(self):
        vacio = real_power()
        for f in vacio:
            f["humedad_raiz"] = None
        with self.assertRaises(pr.ErrorProyeccion):
            pr.proyectar(vacio, respuesta_om())

    def test_respuesta_rara_de_open_meteo_es_un_error_claro(self):
        with self.assertRaises(pr.ErrorProyeccion):
            pr.proyectar(real_power(), {"daily": {}})


class PruebasRuta(unittest.TestCase):
    def setUp(self):
        pr._cache.clear()

    def test_ruta_devuelve_la_proyeccion(self):
        real = AsyncMock(return_value=real_power())
        with TestClient(app) as cliente, patch.object(pr.nasa_power, "diario", real), patch.object(
            pr.openmeteo, "_pedir", AsyncMock(return_value=respuesta_om())
        ):
            r = cliente.get("/api/suelo/proyeccion", params={"lat": 25.8, "lon": -100.0})
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(len(cuerpo["proyeccion"]), 9)
        self.assertIn("tendencia", cuerpo["resumen"])
        self.assertIn("supuestos", cuerpo)

    def test_ruta_503_si_no_hay_dato(self):
        vacio = real_power()
        for f in vacio:
            f["humedad_raiz"] = None
        with TestClient(app) as cliente, patch.object(pr.nasa_power, "diario", AsyncMock(return_value=vacio)), patch.object(
            pr.openmeteo, "_pedir", AsyncMock(return_value=respuesta_om())
        ):
            r = cliente.get("/api/suelo/proyeccion", params={"lat": 25.8, "lon": -100.0})
        self.assertEqual(r.status_code, 503)

    def test_ruta_503_si_open_meteo_no_responde(self):
        falla = AsyncMock(side_effect=pr.OpenMeteoError("Could not get the forecast"))
        with TestClient(app) as cliente, patch.object(pr.nasa_power, "diario", AsyncMock(return_value=real_power())), patch.object(
            pr.openmeteo, "_pedir", falla
        ):
            r = cliente.get("/api/suelo/proyeccion", params={"lat": 25.8, "lon": -100.0})
        self.assertEqual(r.status_code, 503)

    def test_ruta_pide_municipio_o_coordenadas(self):
        with TestClient(app) as cliente:
            r = cliente.get("/api/suelo/proyeccion")
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
