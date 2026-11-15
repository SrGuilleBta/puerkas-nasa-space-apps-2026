"""Pruebas del clima: el respaldo de Open-Meteo y la elección de la fuente (Meteomatics u Open-Meteo)."""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Antes de importar la app: así config.DB_PATH apunta a una base temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import clima as clima_servicio  # noqa: E402
from app.services import meteomatics, openmeteo, suelo_ubicacion  # noqa: E402
from app.services.ubicaciones import Ubicacion  # noqa: E402

LUGAR = Ubicacion(1, "Monterrey, NL", 25.6866, -100.3161, "America/Monterrey")

# Lo que contesta Open-Meteo (recortado a 3 días)
RESPUESTA = {
    "daily": {
        "time": ["2026-11-15", "2026-11-16", "2026-11-17"],
        "temperature_2m_max": [30.1, 20.3, 15.4],
        "temperature_2m_min": [15.9, 13.7, 13.9],
        "precipitation_probability_max": [22, None, 4],
        "weather_code": [51, 3, 0],
    },
    "current": {
        "temperature_2m": 16.2, "apparent_temperature": 17.4, "relative_humidity_2m": 92,
        "wind_speed_10m": 3.2, "weather_code": 0,
    },
}

FALSO_METEOMATICS = {"fuente": "Meteomatics", "pronostico": [], "hoy": {}}
FALSO_OPENMETEO = {"fuente": "Open-Meteo", "pronostico": [], "hoy": {}}


def correr(corutina):
    return asyncio.run(corutina)


class PruebasOpenMeteo(unittest.TestCase):
    def setUp(self):
        openmeteo._cache.clear()

    def test_devuelve_el_mismo_formato_que_meteomatics(self):
        with patch.object(openmeteo, "_pedir", AsyncMock(return_value=RESPUESTA)):
            r = correr(openmeteo.clima(LUGAR))
        self.assertEqual(r["fuente"], "Open-Meteo")
        self.assertEqual([d["fecha"] for d in r["pronostico"]], ["2026-11-15", "2026-11-16", "2026-11-17"])
        primero = r["pronostico"][0]
        self.assertEqual((primero["tmax"], primero["tmin"], primero["lluvia"]), (30, 16, 22))  # redondeados
        self.assertEqual([d["cielo"] for d in r["pronostico"]], ["lluvia", "nube", "sol"])  # llovizna, nublado, despejado
        self.assertIsNone(r["pronostico"][1]["lluvia"])  # un día sin probabilidad no rompe nada
        hoy = r["hoy"]
        self.assertEqual((hoy["temperatura"], hoy["sensacion"], hoy["humedad"], hoy["vientoKmh"]), (16, 17, 92, 3))
        self.assertEqual((hoy["cielo"], hoy["icono"]), ("Clear", "sol"))
        self.assertIs(hoy["optimoParaCampo"], True)  # 16 °C, poco viento y 22 % de lluvia
        self.assertIsNone(hoy["humedadSuelo"])  # la completa el módulo Suelo
        self.assertIsNone(hoy["phSuelo"])

    def test_pide_el_clima_en_la_hora_local_del_lugar(self):
        pedir = AsyncMock(return_value=RESPUESTA)
        with patch.object(openmeteo, "_pedir", pedir):
            correr(openmeteo.clima(LUGAR))
        parametros = pedir.await_args.args[0]
        self.assertEqual((parametros["timezone"], parametros["forecast_days"]), ("America/Monterrey", 7))

    def test_guarda_en_cache_para_no_repetir_la_consulta(self):
        pedir = AsyncMock(return_value=RESPUESTA)
        with patch.object(openmeteo, "_pedir", pedir):
            correr(openmeteo.clima(LUGAR))
            correr(openmeteo.clima(LUGAR))
        self.assertEqual(pedir.await_count, 1)

    def test_una_respuesta_rara_es_un_error_claro(self):
        with patch.object(openmeteo, "_pedir", AsyncMock(return_value={"daily": {}})):
            with self.assertRaises(openmeteo.OpenMeteoError):
                correr(openmeteo.clima(LUGAR))

    def test_codigos_del_tiempo_desconocidos_o_vacios_no_fallan(self):
        self.assertEqual(openmeteo._cielo(None), (None, "nube"))
        self.assertEqual(openmeteo._cielo(1234), (None, "nube"))
        self.assertEqual(openmeteo._cielo(95), ("Thunderstorm", "lluvia"))


class PruebasEleccionDeFuente(unittest.TestCase):
    def con_llaves(self, hay: bool):
        usuario, clave = ("u", "p") if hay else ("", "")
        return patch.multiple(config, METEOMATICS_USER=usuario, METEOMATICS_PASSWORD=clave)

    def test_sin_llaves_usa_open_meteo_sin_tocar_meteomatics(self):
        meteo = AsyncMock(return_value=FALSO_METEOMATICS)
        with self.con_llaves(False), patch.object(meteomatics, "clima", meteo), \
                patch.object(openmeteo, "clima", AsyncMock(return_value=FALSO_OPENMETEO)):
            r = correr(clima_servicio.clima(LUGAR))
        self.assertEqual(r["fuente"], "Open-Meteo")
        meteo.assert_not_awaited()

    def test_con_llaves_prefiere_meteomatics(self):
        respaldo = AsyncMock(return_value=FALSO_OPENMETEO)
        with self.con_llaves(True), patch.object(meteomatics, "clima", AsyncMock(return_value=FALSO_METEOMATICS)), \
                patch.object(openmeteo, "clima", respaldo):
            r = correr(clima_servicio.clima(LUGAR))
        self.assertEqual(r["fuente"], "Meteomatics")
        respaldo.assert_not_awaited()

    def test_si_meteomatics_falla_cae_a_open_meteo(self):
        falla = AsyncMock(side_effect=meteomatics.MeteomaticsError("Meteomatics responded with 500"))
        with self.con_llaves(True), patch.object(meteomatics, "clima", falla), \
                patch.object(openmeteo, "clima", AsyncMock(return_value=FALSO_OPENMETEO)):
            r = correr(clima_servicio.clima(LUGAR))
        self.assertEqual(r["fuente"], "Open-Meteo")

    def test_si_todo_falla_el_error_dice_que_paso(self):
        sin_respaldo = AsyncMock(side_effect=openmeteo.OpenMeteoError("Could not get the forecast from Open-Meteo"))
        falla = AsyncMock(side_effect=meteomatics.MeteomaticsError("Meteomatics rejected the username or password"))
        with self.con_llaves(True), patch.object(meteomatics, "clima", falla), patch.object(openmeteo, "clima", sin_respaldo):
            with self.assertRaises(clima_servicio.ClimaNoDisponible) as c:
                correr(clima_servicio.clima(LUGAR))
        self.assertIn("rejected", str(c.exception))
        self.assertIn("Open-Meteo", str(c.exception))
        with self.con_llaves(False), patch.object(openmeteo, "clima", sin_respaldo):
            with self.assertRaises(clima_servicio.ClimaNoDisponible) as c:
                correr(clima_servicio.clima(LUGAR))
        self.assertIn("No Meteomatics keys", str(c.exception))


class PruebasEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if Path(config.DB_PATH).name == "planificador.db":
            raise RuntimeError("Las pruebas apuntan a la base real; define PLANIFICADOR_DB antes de importar app")
        cls._ctx = TestClient(app)
        cls.c = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def test_clima_responde_con_el_respaldo_e_indica_la_fuente(self):
        datos = {**FALSO_OPENMETEO, "hoy": {"temperatura": 16, "humedadSuelo": None, "phSuelo": None}}
        with patch.object(clima_servicio, "clima", AsyncMock(return_value=datos)), \
                patch.object(suelo_ubicacion, "ph", AsyncMock(return_value=7.6)), \
                patch.object(suelo_ubicacion, "humedad_raiz", AsyncMock(return_value=42.0)):
            r = self.c.get("/api/principal/clima", params={"municipio": "Monterrey, NL"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["fuente"], "Open-Meteo")
        self.assertEqual((r.json()["hoy"]["phSuelo"], r.json()["hoy"]["humedadSuelo"]), (7.6, 42))  # lo agrega Suelo

    def test_clima_y_alertas_dan_502_si_ninguna_fuente_responde(self):
        error = AsyncMock(side_effect=clima_servicio.ClimaNoDisponible("nada responde"))
        with patch.object(clima_servicio, "clima", error), \
                patch.object(suelo_ubicacion, "ph", AsyncMock(return_value=None)), \
                patch.object(suelo_ubicacion, "humedad_raiz", AsyncMock(return_value=None)):
            clima = self.c.get("/api/principal/clima", params={"municipio": "Monterrey, NL"})
            alertas = self.c.get("/api/principal/alertas", params={"municipio": "Monterrey, NL"})
        self.assertEqual((clima.status_code, alertas.status_code), (502, 502))
        self.assertIn("nada responde", clima.json()["detail"])


if __name__ == "__main__":
    unittest.main()
