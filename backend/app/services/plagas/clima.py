"""Serie diaria de clima para evaluar plagas: 3 días pasados y 7 de pronóstico (Open-Meteo, gratis y sin llave).

El motor necesita la humedad relativa de cada día, que el pronóstico de Principal no trae (solo la de ahora),
por eso consulta Open-Meteo directamente. La probabilidad de lluvia no existe para los días pasados: ahí se
usa la lluvia medida (100 si cayó 1 mm o más, 0 si no).
"""

import time

import httpx

URL = "https://api.open-meteo.com/v1/forecast"
SEGUNDOS_CACHE = 1800  # media hora
DIAS_PASADOS = 3
DIAS_PRONOSTICO = 7
DIARIAS = (
    "temperature_2m_max,temperature_2m_min,temperature_2m_mean,relative_humidity_2m_mean,"
    "precipitation_probability_max,precipitation_sum"
)

_cache: dict[str, tuple[float, list[dict]]] = {}


class ErrorClima(Exception):
    """Open-Meteo no respondió o mandó algo inesperado."""


def serie_desde_respuesta(datos: dict) -> list[dict]:
    """Días con todos los datos que usa el motor (los incompletos se omiten)."""
    try:
        d = datos["daily"]
        dias = []
        for i, fecha in enumerate(d["time"]):
            tmax, tmin = d["temperature_2m_max"][i], d["temperature_2m_min"][i]
            tmed, humedad = d["temperature_2m_mean"][i], d["relative_humidity_2m_mean"][i]
            if None in (tmax, tmin, tmed, humedad):
                continue
            lluvia = d["precipitation_probability_max"][i]
            if lluvia is None:  # día pasado: se deduce de la lluvia medida
                lluvia = 100 if (d["precipitation_sum"][i] or 0) >= 1 else 0
            dias.append({"fecha": fecha, "tmax": tmax, "tmin": tmin, "tmed": round(tmed, 1),
                         "humedad": humedad, "lluvia": lluvia})
        return dias
    except (KeyError, IndexError, TypeError) as e:
        raise ErrorClima(f"Open-Meteo sent an unexpected answer ({type(e).__name__})") from e


async def serie(cliente: httpx.AsyncClient, lat: float, lon: float, zona: str) -> list[dict]:
    llave = f"{lat:.2f},{lon:.2f}"
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]
    parametros = {
        "latitude": lat, "longitude": lon, "timezone": zona,
        "past_days": DIAS_PASADOS, "forecast_days": DIAS_PRONOSTICO, "daily": DIARIAS,
    }
    try:
        r = await cliente.get(URL, params=parametros)
        r.raise_for_status()
        dias = serie_desde_respuesta(r.json())
    except (httpx.HTTPError, ValueError) as e:
        raise ErrorClima(f"Could not get the weather series from Open-Meteo ({type(e).__name__})") from e
    if not dias:
        raise ErrorClima("Open-Meteo sent no usable days")
    _cache[llave] = (time.monotonic(), dias)
    return dias
