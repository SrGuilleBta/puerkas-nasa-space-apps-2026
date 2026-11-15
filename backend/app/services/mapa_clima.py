"""Mapa de Clima: lluvia y calor del pronóstico de 7 días sobre todo México.

La fuente es Open-Meteo (gratis y sin llave), que acepta muchas coordenadas en una sola consulta. Se pide una
malla de puntos cada `PASO` grados que cae dentro del contorno de México (unas 110 coordenadas) más los lugares
guardados por la persona usuaria, y el frontend pinta los valores como manchas de color sobre el contorno.

Por qué no NASA: POWER y GPM IMERG traen lluvia observada con 2-3 días de retraso y no pronóstico, y IMERG pide
cuenta de Earthdata y descargar imágenes grandes. Aquí se quiere ver qué viene, así que se usa el pronóstico. La
lluvia observada de NASA POWER ya se muestra en Planificador (Crop guide) por ubicación.

Límite de consultas: la malla cuenta como ~110 consultas de Open-Meteo (gratis: 10 000 al día). Con la caché de
`SEGUNDOS_CACHE` son unas 900 al día como máximo, sin importar cuánta gente abra la pantalla. Si Open-Meteo falla y
hay una copia vieja, se devuelve esa con `desactualizado` en verdadero.

Los valores son del modelo en cada punto de la malla (no de estaciones): sirven para ver el patrón regional, no para
saber cuánto llueve en una parcela.
"""

import asyncio
import time
from datetime import datetime, timezone
from functools import lru_cache

import httpx

URL = "https://api.open-meteo.com/v1/forecast"
PASO = 1.5  # grados entre puntos de la malla (~165 km)
DIAS = 7
ZONA = "America/Mexico_City"
SEGUNDOS_CACHE = 3 * 3600
POR_CONSULTA = 50  # coordenadas por petición (la URL no crece sin límite)

# Contorno simplificado de México como (longitud, latitud), siguiendo costas y fronteras. No es cartografía oficial:
# solo sirve para dibujar el mapa y para elegir qué puntos de la malla están dentro del país.
CONTORNO = [
    (-117.12, 32.53), (-116.85, 31.95), (-116.62, 31.87), (-116.0, 30.4), (-115.8, 29.95), (-115.05, 27.85),
    (-114.2, 27.1), (-113.6, 26.7), (-112.9, 25.6), (-112.15, 24.6), (-111.9, 24.2), (-110.6, 23.3),
    (-109.9, 22.9), (-109.7, 23.65), (-110.3, 24.15), (-110.9, 24.8), (-111.3, 25.9), (-111.98, 26.9),
    (-112.27, 27.33), (-112.85, 28.4), (-113.55, 29.0), (-114.1, 29.8), (-114.8, 31.0), (-114.75, 31.5),
    (-114.8, 31.75), (-113.5, 31.3), (-112.9, 31.0), (-112.3, 29.8), (-112.0, 28.8), (-111.1, 28.0),
    (-110.9, 27.9), (-110.4, 27.2), (-109.5, 26.7), (-109.05, 25.6), (-108.4, 25.2), (-107.9, 24.6),
    (-106.4, 23.2), (-105.7, 22.2), (-105.3, 21.55), (-105.55, 20.75), (-105.25, 20.6), (-105.7, 20.4),
    (-104.7, 19.2), (-104.35, 19.05), (-103.5, 18.3), (-102.2, 17.95), (-101.55, 17.65), (-99.9, 16.85),
    (-98.5, 16.3), (-97.1, 15.85), (-96.1, 15.75), (-95.2, 16.2), (-94.5, 16.2), (-93.8, 15.8),
    (-93.0, 15.0), (-92.2, 14.53), (-92.1, 15.07), (-91.75, 16.07), (-90.4, 16.1), (-90.45, 17.82),
    (-89.15, 17.82), (-88.9, 17.9), (-88.3, 18.5), (-87.85, 18.2), (-87.7, 18.7), (-87.45, 20.2),
    (-87.0, 20.7), (-86.8, 21.15), (-86.8, 21.5), (-87.05, 21.6), (-88.3, 21.55), (-89.0, 21.4),
    (-89.65, 21.3), (-90.3, 21.1), (-90.4, 20.85), (-90.45, 20.2), (-90.55, 19.85), (-90.7, 19.3),
    (-91.1, 18.85), (-91.8, 18.65), (-92.65, 18.55), (-93.2, 18.4), (-93.9, 18.4), (-94.4, 18.15),
    (-95.1, 18.7), (-95.75, 18.8), (-96.1, 19.2), (-96.8, 20.2), (-97.4, 20.95), (-97.7, 21.5),
    (-97.85, 22.25), (-97.75, 22.8), (-97.7, 23.8), (-97.65, 24.5), (-97.7, 25.0), (-97.2, 25.9),
    (-97.5, 25.88), (-98.3, 26.1), (-99.1, 26.4), (-99.5, 27.5), (-100.3, 28.3), (-100.5, 28.7),
    (-101.0, 29.4), (-102.3, 29.88), (-102.7, 29.75), (-103.15, 28.97), (-104.5, 29.65), (-104.7, 30.15),
    (-105.0, 30.7), (-106.0, 31.35), (-106.5, 31.75), (-108.2, 31.78), (-108.2, 31.33), (-111.07, 31.33),
    (-114.8, 32.5), (-114.72, 32.72),
]

_cache: dict[str, tuple[float, dict]] = {}


class ErrorMapaClima(Exception):
    """No se pudo obtener el pronóstico del mapa y no hay una copia anterior."""


def _dentro(lon: float, lat: float) -> bool:
    """Punto dentro del contorno (regla de cruce de rayos)."""
    dentro = False
    n = len(CONTORNO)
    for i in range(n):
        x1, y1 = CONTORNO[i]
        x2, y2 = CONTORNO[(i + 1) % n]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


@lru_cache(maxsize=1)
def malla() -> list[tuple[float, float]]:
    """Puntos (lat, lon) de la malla que caen dentro de México."""
    lons = [c[0] for c in CONTORNO]
    lats = [c[1] for c in CONTORNO]
    puntos = []
    lat = min(lats) + PASO / 2
    while lat < max(lats):
        lon = min(lons) + PASO / 2
        while lon < max(lons):
            if _dentro(lon, lat):
                puntos.append((round(lat, 2), round(lon, 2)))
            lon += PASO
        lat += PASO
    return puntos


def caja() -> dict:
    lons = [c[0] for c in CONTORNO]
    lats = [c[1] for c in CONTORNO]
    return {"lonMin": min(lons), "lonMax": max(lons), "latMin": min(lats), "latMax": max(lats)}


def _numero(v):
    return None if v is None else round(float(v), 1)


def _leer(respuesta, cuantos: int) -> list[dict]:
    """Convierte la respuesta de Open-Meteo (un objeto con una coordenada, o una lista con varias) en
    [{"fechas": [...], "lluviaMm": [...], "tmax": [...]}]."""
    lista = respuesta if isinstance(respuesta, list) else [respuesta]
    if len(lista) != cuantos:
        raise ValueError("number of points does not match")
    salida = []
    for punto in lista:
        d = punto["daily"]
        salida.append(
            {
                "fechas": list(d["time"]),
                "lluviaMm": [_numero(v) for v in d["precipitation_sum"]],
                "tmax": [_numero(v) for v in d["temperature_2m_max"]],
            }
        )
    return salida


async def _pedir_lote(cliente: httpx.AsyncClient, coordenadas: list[tuple[float, float]]) -> list[dict]:
    parametros = {
        "latitude": ",".join(str(lat) for lat, _ in coordenadas),
        "longitude": ",".join(str(lon) for _, lon in coordenadas),
        "daily": "precipitation_sum,temperature_2m_max",
        "timezone": ZONA,
        "forecast_days": DIAS,
    }
    r = await cliente.get(URL, params=parametros)
    r.raise_for_status()
    return _leer(r.json(), len(coordenadas))


async def _pedir(coordenadas: list[tuple[float, float]]) -> list[dict]:
    lotes = [coordenadas[i : i + POR_CONSULTA] for i in range(0, len(coordenadas), POR_CONSULTA)]
    try:
        async with httpx.AsyncClient(timeout=30) as cliente:
            resultados = await asyncio.gather(*(_pedir_lote(cliente, lote) for lote in lotes))
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        raise ErrorMapaClima(f"Could not get the map forecast from Open-Meteo ({type(e).__name__})") from e
    return [p for lote in resultados for p in lote]


def _fechas_comunes(puntos: list[dict]) -> list[str]:
    """Las fechas del pronóstico; si algún punto trae menos días, se usan los que todos tienen."""
    fechas = min((p["fechas"] for p in puntos), key=len)
    for p in puntos:
        p["lluviaMm"] = p["lluviaMm"][: len(fechas)]
        p["tmax"] = p["tmax"][: len(fechas)]
    return fechas


async def mapa(lugares: list[tuple[str, float, float]]) -> dict:
    """Pronóstico de lluvia (mm al día) y temperatura máxima (°C) de la malla de México y de `lugares`
    ((nombre, lat, lon) de las ubicaciones guardadas)."""
    llave = "|".join(f"{lat:.2f},{lon:.2f}" for _, lat, lon in lugares)
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    grilla = malla()
    coordenadas = list(grilla) + [(round(lat, 2), round(lon, 2)) for _, lat, lon in lugares]
    try:
        valores = await _pedir(coordenadas)
    except ErrorMapaClima:
        if guardado:  # una copia vieja sirve más que un error
            return {**guardado[1], "desactualizado": True}
        raise

    fechas = _fechas_comunes(valores)
    n = len(grilla)
    resultado = {
        "fuente": "Open-Meteo",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "desactualizado": False,
        "dias": fechas,
        "paso": PASO,
        "caja": caja(),
        "contorno": [list(c) for c in CONTORNO],
        "puntos": [
            {"lat": lat, "lon": lon, "lluviaMm": v["lluviaMm"], "tmax": v["tmax"]}
            for (lat, lon), v in zip(grilla, valores[:n])
        ],
        "lugares": [
            {"nombre": nombre, "lat": lat, "lon": lon, "lluviaMm": v["lluviaMm"], "tmax": v["tmax"]}
            for (nombre, lat, lon), v in zip(lugares, valores[n:])
        ],
    }
    _cache[llave] = (time.monotonic(), resultado)
    return resultado
