"""Clima observado por satélite de NASA POWER (https://power.larc.nasa.gov), gratis y sin llave.

Sirve para ver qué pasó en el campo (lluvia, temperatura, radiación y humedad de la raíz) en un
periodo, por ejemplo desde que se sembró. Los datos llevan unos 2 días de retraso, y los días sin
dato vienen como -999, que aquí se ignoran.
"""

import time
from datetime import date

import httpx

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETROS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,GWETROOT"
MAX_DIAS = 400
SEGUNDOS_CACHE = 6 * 3600  # los datos diarios casi no cambian

_cache: dict[tuple, tuple[float, dict]] = {}


class ErrorNasaPower(Exception):
    pass


def _valores(parametro: dict | None) -> list[float]:
    return [v for v in (parametro or {}).values() if v is not None and v > -900]


def _media(valores: list[float], decimales: int = 1) -> float | None:
    return round(sum(valores) / len(valores), decimales) if valores else None


def resumir(p: dict) -> dict:
    """Resume las series diarias de POWER (`properties.parameter`) en pocas cifras útiles."""
    lluvia = _valores(p.get("PRECTOTCORR"))
    suelo = _valores(p.get("GWETROOT"))
    tmax = _valores(p.get("T2M_MAX"))
    tmin = _valores(p.get("T2M_MIN"))
    return {
        "dias": max(len(lluvia), len(_valores(p.get("T2M")))),
        "lluviaMm": round(sum(lluvia)) if lluvia else None,
        "diasConLluvia": sum(1 for v in lluvia if v >= 1),
        "tempMedia": _media(_valores(p.get("T2M"))),
        "tempMax": round(max(tmax), 1) if tmax else None,
        "tempMin": round(min(tmin), 1) if tmin else None,
        "radiacion": _media(_valores(p.get("ALLSKY_SFC_SW_DWN"))),  # MJ/m² al día (unidad de POWER para la comunidad AG)
        "humedadRaizPct": round(_media(suelo, 2) * 100) if suelo else None,
    }


async def periodo(lat: float, lon: float, desde: date, hasta: date) -> dict:
    if hasta < desde:
        raise ValueError("The end date is before the start date")
    if (hasta - desde).days > MAX_DIAS:
        raise ValueError(f"The period cannot exceed {MAX_DIAS} days")

    llave = (round(lat, 3), round(lon, 3), desde, hasta)
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    params = {
        "parameters": PARAMETROS,
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": desde.strftime("%Y%m%d"),
        "end": hasta.strftime("%Y%m%d"),
        "format": "JSON",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as cliente:
            r = await cliente.get(URL, params=params)
            r.raise_for_status()
        serie = r.json()["properties"]["parameter"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise ErrorNasaPower(f"Could not query NASA POWER ({type(e).__name__})") from e

    resultado = {"desde": desde.isoformat(), "hasta": hasta.isoformat(), **resumir(serie)}
    _cache[llave] = (time.monotonic(), resultado)
    return resultado
