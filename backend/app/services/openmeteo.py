"""Respaldo del clima: Open-Meteo (https://open-meteo.com), gratis y sin llave.

Devuelve lo mismo que `meteomatics.clima` (pronóstico de 7 días y condiciones de hoy), para que Principal,
las alertas y Noticias funcionen igual cuando Meteomatics no tiene llaves o no responde. Los dos
modelos no coinciden (p. ej. la probabilidad de lluvia de un día puede diferir mucho), por eso el
resultado trae `fuente` y la pantalla la muestra.
"""

import time
from datetime import datetime, timezone

import httpx

from app.services.meteomatics import _optimo_para_campo
from app.services.ubicaciones import Ubicacion

URL = "https://api.open-meteo.com/v1/forecast"
SEGUNDOS_CACHE = 600  # 10 minutos, igual que Meteomatics

_cache: dict[str, tuple[float, dict]] = {}

# Códigos del tiempo (WMO) -> (texto, icono para el frontend: sol, nube o lluvia)
CODIGOS = {
    0: ("Clear", "sol"),
    1: ("Mostly clear", "sol"),
    2: ("Partly cloudy", "nube"),
    3: ("Cloudy", "nube"),
    45: ("Fog", "nube"),
    48: ("Fog", "nube"),
    51: ("Drizzle", "lluvia"), 53: ("Drizzle", "lluvia"), 55: ("Drizzle", "lluvia"),
    56: ("Freezing drizzle", "lluvia"), 57: ("Freezing drizzle", "lluvia"),
    61: ("Rain", "lluvia"), 63: ("Rain", "lluvia"), 65: ("Rain", "lluvia"),
    66: ("Freezing rain", "lluvia"), 67: ("Freezing rain", "lluvia"),
    71: ("Snow", "lluvia"), 73: ("Snow", "lluvia"), 75: ("Snow", "lluvia"), 77: ("Snow", "lluvia"),
    80: ("Showers", "lluvia"), 81: ("Showers", "lluvia"), 82: ("Showers", "lluvia"),
    85: ("Snow showers", "lluvia"), 86: ("Snow showers", "lluvia"),
    95: ("Thunderstorm", "lluvia"), 96: ("Thunderstorm", "lluvia"), 99: ("Thunderstorm", "lluvia"),
}


class OpenMeteoError(Exception):
    pass


def _cielo(codigo) -> tuple[str | None, str]:
    """(texto, icono) de un código del tiempo; sin dato, nublado."""
    if codigo is None:
        return None, "nube"
    return CODIGOS.get(int(codigo), (None, "nube"))


def _redondear(valor):
    return None if valor is None else int(round(valor))


async def _pedir(parametros: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15) as cliente:
            r = await cliente.get(URL, params=parametros)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise OpenMeteoError(f"Could not get the forecast from Open-Meteo ({type(e).__name__})") from e


async def clima(m: Ubicacion) -> dict:
    llave = f"{m.lat:.3f},{m.lon:.3f}"
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    parametros = {
        "latitude": m.lat,
        "longitude": m.lon,
        "timezone": m.zona,  # así el primer día es hoy en la hora local del lugar
        "forecast_days": 7,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
    }
    datos = await _pedir(parametros)
    try:
        diario, actual = datos["daily"], datos["current"]
        pronostico = [
            {
                "fecha": diario["time"][i],
                "tmax": _redondear(diario["temperature_2m_max"][i]),
                "tmin": _redondear(diario["temperature_2m_min"][i]),
                "lluvia": _redondear(diario["precipitation_probability_max"][i]),
                "cielo": _cielo(diario["weather_code"][i])[1],
            }
            for i in range(len(diario["time"]))
        ]
    except (KeyError, IndexError, TypeError) as e:
        raise OpenMeteoError(f"Open-Meteo sent an unexpected answer ({type(e).__name__})") from e

    texto, icono = _cielo(actual.get("weather_code"))
    temperatura, viento = actual.get("temperature_2m"), actual.get("wind_speed_10m")
    resultado = {
        "municipio": m.nombre,
        "fuente": "Open-Meteo",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "pronostico": pronostico,
        "hoy": {
            "temperatura": _redondear(temperatura),
            "sensacion": _redondear(actual.get("apparent_temperature")),
            "cielo": texto,
            "icono": icono,
            "optimoParaCampo": _optimo_para_campo(temperatura, viento, pronostico[0]["lluvia"] if pronostico else None),
            "humedad": _redondear(actual.get("relative_humidity_2m")),
            "vientoKmh": _redondear(viento),
            # Open-Meteo mide humedad volumétrica de la capa superficial: no es la misma escala que la humedad
            # de la zona de raíz que muestra Principal, así que se deja vacía y la completa el módulo Suelo.
            "humedadSuelo": None,
            "phSuelo": None,
        },
    }
    _cache[llave] = (time.monotonic(), resultado)
    return resultado
