"""Condiciones locales de la pantalla Clima: cómo está el día en la ubicación activa y hasta cuándo se puede trabajar.

Sale de Open-Meteo (gratis y sin llave) por hora, para tener lo que Principal no trae: dirección del viento, lluvia
esperada en mm, temperatura del suelo y la "ventana para labores". La humedad del suelo la pone el router con el
módulo Suelo (NASA POWER), la misma cifra que Principal y la pantalla Soil.

Ventana para labores: regla nuestra, no un dato oficial. Una hora sirve para el campo si la temperatura está entre
10 y 35 °C, el viento es menor de 25 km/h y la probabilidad de lluvia es menor de 30 % (los mismos límites que
`meteomatics._optimo_para_campo`). La ventana va desde la hora actual hasta la primera hora que ya no sirve (dentro del
día local). Si la hora actual no sirve, se avisa cuándo empieza la siguiente que sí.

La temperatura del suelo es la de 18 cm (la profundidad más cercana a los 20 cm del diseño).
"""

import time
from datetime import datetime, timezone

from app.services import openmeteo
from app.services.openmeteo import OpenMeteoError
from app.services.ubicaciones import Ubicacion

SEGUNDOS_CACHE = 600  # 10 minutos, igual que el clima de Principal
TEMP_MIN, TEMP_MAX = 10, 35
VIENTO_MAX = 25  # km/h
LLUVIA_MAX = 30  # % de probabilidad

_cache: dict[str, tuple[float, dict]] = {}

PUNTOS_CARDINALES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def punto_cardinal(grados) -> str | None:
    """De dónde viene el viento (N, NE, E...), a partir de los grados."""
    if grados is None:
        return None
    return PUNTOS_CARDINALES[int(((grados % 360) + 22.5) // 45) % 8]


def _sirve(temperatura, viento, lluvia) -> bool:
    """Si una hora sirve para labores de campo. Sin dato de algo, no se da por buena."""
    if None in (temperatura, viento, lluvia):
        return False
    return TEMP_MIN <= temperatura <= TEMP_MAX and viento < VIENTO_MAX and lluvia < LLUVIA_MAX


def ventana(horas: list[dict], hora_actual: int) -> dict:
    """Ventana para labores a partir de las horas del día local ({hora, temperatura, vientoKmh, lluvia})."""
    restantes = [h for h in horas if h["hora"] >= hora_actual]
    buenas = [_sirve(h["temperatura"], h["vientoKmh"], h["lluvia"]) for h in restantes]
    if not restantes or not any(buenas):
        return {"favorable": False, "desde": None, "hasta": None, "motivo": "no_hours"}
    if buenas[0]:
        fin = next((h["hora"] for h, b in zip(restantes, buenas) if not b), None)
        return {"favorable": True, "desde": None, "hasta": None if fin is None else f"{fin:02d}:00"}
    inicio = restantes[buenas.index(True)]["hora"]
    return {"favorable": False, "desde": f"{inicio:02d}:00", "hasta": None}


def _horas(h: dict) -> list[dict]:
    return [
        {
            "hora": int(h["time"][i][11:13]),
            "temperatura": h["temperature_2m"][i],
            "vientoKmh": h["wind_speed_10m"][i],
            "lluvia": h["precipitation_probability"][i],
        }
        for i in range(len(h["time"]))
    ]


async def condiciones(m: Ubicacion) -> dict:
    llave = f"{m.lat:.3f},{m.lon:.3f}"
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    datos = await openmeteo._pedir({
        "latitude": m.lat,
        "longitude": m.lon,
        "timezone": m.zona,  # la hora y el día son los del lugar
        "forecast_days": 1,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "hourly": "temperature_2m,wind_speed_10m,precipitation_probability,soil_temperature_18cm",
        "daily": "precipitation_sum,precipitation_probability_max",
    })
    try:
        actual, por_hora, diario = datos["current"], datos["hourly"], datos["daily"]
        hora_actual = int(actual["time"][11:13])
        horas = _horas(por_hora)
        indice = next((i for i, h in enumerate(horas) if h["hora"] == hora_actual), None)
        texto, icono = openmeteo._cielo(actual.get("weather_code"))
        resultado = {
            "municipio": m.nombre,
            "fuente": "Open-Meteo",
            "actualizado": datetime.now(timezone.utc).isoformat(),
            "temperatura": openmeteo._redondear(actual.get("temperature_2m")),
            "sensacion": openmeteo._redondear(actual.get("apparent_temperature")),
            "cielo": texto,
            "icono": icono,
            "humedad": openmeteo._redondear(actual.get("relative_humidity_2m")),
            "vientoKmh": openmeteo._redondear(actual.get("wind_speed_10m")),
            "vientoDireccion": punto_cardinal(actual.get("wind_direction_10m")),
            "lluviaProbabilidad": openmeteo._redondear(diario["precipitation_probability_max"][0]),
            "lluviaMm": None if diario["precipitation_sum"][0] is None else round(diario["precipitation_sum"][0], 1),
            "temperaturaSuelo": None if indice is None else openmeteo._redondear(por_hora["soil_temperature_18cm"][indice]),
            "humedadSuelo": None,  # la completa el router con el módulo Suelo
            "ventana": ventana(horas, hora_actual),
        }
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise OpenMeteoError(f"Open-Meteo sent an unexpected answer ({type(e).__name__})") from e

    _cache[llave] = (time.monotonic(), resultado)
    return resultado
