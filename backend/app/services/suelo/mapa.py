"""Mapa de Suelo: humedad y temperatura del suelo sobre todo México, con NASA POWER.

Usa la API regional de POWER (https://power.larc.nasa.gov/docs/services/api/temporal/daily/), que devuelve la
malla nativa de 0.5° (lat) × 0.625° (lon) de un recuadro en una sola consulta. Límites de POWER (probados el
15-nov-2026): un parámetro por consulta y recuadros de máximo 10° × 10°. México cabe en 2 × 4 recuadros, así que
son 8 consultas por capa (~1 s cada una). Sin llave.

Capas (del modelo de NASA, no son mediciones en la parcela):
- GWETROOT: humedad de la zona de raíces (0-100 cm), fracción de saturación (0-1, se pasa a %).
- GWETTOP: humedad superficial (0-5 cm), fracción de saturación.
- TS: temperatura de la superficie de la tierra (°C).

Cada punto lleva el promedio de los últimos `DIAS_PROMEDIO` días con dato (POWER llega con 2-3 días de retraso).
No se compara contra otros años: POWER cambió de modelo el 1-oct-2026 (MERRA-2 → GEOS-IT) y esa comparación da
sequías falsas (ver docs/suelo.md); para eso está /api/suelo/estado con SMAP.

Se usa el mismo contorno de México que el mapa de Clima (services/mapa_clima.py) para elegir los puntos y dibujarlo.
Caché de `SEGUNDOS_CACHE`: los datos diarios de POWER cambian una vez al día.
"""

import asyncio
import time
from datetime import date, datetime, timedelta, timezone

import httpx

from app.services import mapa_clima

URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"
CAPAS = {"humedad_raiz": "GWETROOT", "humedad_superficie": "GWETTOP", "temperatura": "TS"}
# Recuadros de 10° × 10° que cubren el contorno de México (lat 14.5-32.7, lon -117.1 a -86.7)
RECUADROS = [
    (lat, lat + 10, lon, lon + 10)
    for lat in (14, 24)
    for lon in (-118, -108, -98, -88)
]
DIAS_CONSULTA = 12  # se piden de más por el retraso de POWER
DIAS_PROMEDIO = 7
PASO_LON = 0.625
CONSULTAS_SIMULTANEAS = 4
SEGUNDOS_CACHE = 12 * 3600

_cache: dict[str, tuple[float, dict]] = {}


class ErrorMapaSuelo(Exception):
    """POWER no respondió y no hay una copia anterior."""


async def _recuadro(cliente: httpx.AsyncClient, parametro: str, caja: tuple, inicio: str, fin: str) -> dict:
    """{(lat, lon): {fecha: valor}} de un recuadro (sin los -999 de mar o sin dato)."""
    lat0, lat1, lon0, lon1 = caja
    r = await cliente.get(URL, params={
        "parameters": parametro, "community": "AG", "format": "JSON",
        "latitude-min": lat0, "latitude-max": lat1, "longitude-min": lon0, "longitude-max": lon1,
        "start": inicio, "end": fin,
    })
    r.raise_for_status()
    salida = {}
    for f in r.json().get("features", []):
        lon, lat = f["geometry"]["coordinates"][:2]
        serie = {d: v for d, v in f["properties"]["parameter"][parametro].items() if v is not None and v > -900}
        if serie:
            salida[(round(lat, 3), round(lon, 3))] = serie
    return salida


def _promedio(serie: dict) -> tuple[float | None, str | None]:
    """Promedio de los últimos DIAS_PROMEDIO días con dato y la fecha más reciente."""
    fechas = sorted(serie)[-DIAS_PROMEDIO:]
    if not fechas:
        return None, None
    return sum(serie[d] for d in fechas) / len(fechas), fechas[-1]


def _cercano(puntos: list[dict], lat: float, lon: float) -> dict | None:
    """Punto de la malla más cercano a un lugar (a menos de ~1 celda)."""
    mejor = min(puntos, key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2, default=None)
    if mejor and abs(mejor["lat"] - lat) <= 0.5 and abs(mejor["lon"] - lon) <= PASO_LON:
        return mejor
    return None


async def mapa(lugares: list[tuple[str, float, float]]) -> dict:
    llave = "|".join(f"{lat:.2f},{lon:.2f}" for _, lat, lon in lugares)
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    hoy = date.today()
    inicio = (hoy - timedelta(days=DIAS_CONSULTA)).strftime("%Y%m%d")
    fin = (hoy - timedelta(days=1)).strftime("%Y%m%d")
    semaforo = asyncio.Semaphore(CONSULTAS_SIMULTANEAS)

    async def una(cliente, capa, caja):
        async with semaforo:
            return capa, await _recuadro(cliente, CAPAS[capa], caja, inicio, fin)

    try:
        async with httpx.AsyncClient(timeout=90) as cliente:
            partes = await asyncio.gather(*(una(cliente, c, caja) for c in CAPAS for caja in RECUADROS))
    except (httpx.HTTPError, ValueError, KeyError) as e:
        if guardado:
            return {**guardado[1], "desactualizado": True}
        raise ErrorMapaSuelo(f"NASA POWER did not answer ({type(e).__name__}). Please try again in a moment.") from e

    # Junta los recuadros (los bordes se repiten entre recuadros vecinos)
    series: dict[str, dict] = {c: {} for c in CAPAS}
    for capa, datos in partes:
        series[capa].update(datos)

    puntos = []
    ultima = None
    for (lat, lon), serie_raiz in series["humedad_raiz"].items():
        if not mapa_clima._dentro(lon, lat):
            continue
        punto = {"lat": lat, "lon": lon}
        for capa in CAPAS:
            valor, fecha = _promedio(series[capa].get((lat, lon), {}))
            if valor is not None and capa != "temperatura":
                valor *= 100  # fracción de saturación → %
            punto[capa] = None if valor is None else round(valor, 1)
            if fecha and (ultima is None or fecha > ultima):
                ultima = fecha
        puntos.append(punto)
    if not puntos:
        raise ErrorMapaSuelo("NASA POWER returned no soil data for Mexico")

    resultado = {
        "fuente": "NASA POWER (GWETROOT, GWETTOP, TS)",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "desactualizado": False,
        "hasta": f"{ultima[:4]}-{ultima[4:6]}-{ultima[6:]}" if ultima else None,
        "dias_promedio": DIAS_PROMEDIO,
        "paso": PASO_LON,
        "caja": mapa_clima.caja(),
        "contorno": [list(c) for c in mapa_clima.CONTORNO],
        "puntos": puntos,
        "lugares": [
            {"nombre": nombre, "lat": lat, "lon": lon,
             **{c: (p or {}).get(c) for c in CAPAS}}
            for nombre, lat, lon in lugares
            for p in [_cercano(puntos, lat, lon)]
        ],
    }
    _cache[llave] = (time.monotonic(), resultado)
    return resultado
