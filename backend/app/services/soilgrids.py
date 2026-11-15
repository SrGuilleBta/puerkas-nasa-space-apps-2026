"""pH del suelo con SoilGrids (https://rest.isric.org). No necesita llave.

El suelo casi no cambia, así que el resultado se guarda 24 horas; SoilGrids limita las
consultas (unas 5 por minuto) y es lento. Si falla, se devuelve None en vez de romper la
pantalla, y no se vuelve a intentar durante unos minutos.

SoilGrids no tiene dato en zonas urbanas (el centro de una ciudad devuelve null) y al agricultor
le sirve el suelo del campo. Las ciudades de inicio traen un punto de campo verificado; en un lugar
nuevo se prueba el punto mismo y, si no hay dato, unos puntos cercanos hasta encontrar uno.
"""

import logging
import time

import httpx

from app.services.ubicaciones import Ubicacion

log = logging.getLogger(__name__)

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROFUNDIDADES = ["0-5cm", "5-15cm", "15-30cm"]  # zona de raíces
SEGUNDOS_CACHE = 24 * 3600
SEGUNDOS_CACHE_FALLO = 300

# Desplazamientos (grados de latitud, longitud) que se prueban, en orden, si el punto no tiene dato.
# 0.1° son unos 11 km: primero los 4 lados cercanos y luego las 4 esquinas, más lejos.
VECINOS = [(0.1, 0), (0, 0.1), (-0.1, 0), (0, -0.1), (0.2, 0.2), (-0.2, 0.2), (0.2, -0.2), (-0.2, -0.2)]

_cache: dict[str, tuple[float, float | None]] = {}


def _puntos(m: Ubicacion) -> list[tuple[float, float]]:
    if m.lat_suelo is not None and m.lon_suelo is not None:
        return [(m.lat_suelo, m.lon_suelo)]  # ya verificado: no hace falta buscar otro
    return [(m.lat, m.lon)] + [(m.lat + dy, m.lon + dx) for dy, dx in VECINOS]


async def _consultar_punto(cliente: httpx.AsyncClient, lat: float, lon: float) -> float | None:
    """pH promedio de los primeros 30 cm en un punto, o None si SoilGrids no tiene dato ahí."""
    params = [
        ("lon", lon),
        ("lat", lat),
        ("property", "phh2o"),
        ("value", "mean"),
        *[("depth", p) for p in PROFUNDIDADES],
    ]
    r = await cliente.get(URL, params=params)
    r.raise_for_status()
    profundidades = r.json()["properties"]["layers"][0]["depths"]
    medias = [d["values"]["mean"] for d in profundidades if d["values"]["mean"] is not None]
    if not medias:
        return None
    # SoilGrids guarda el pH multiplicado por 10 (77 significa pH 7.7)
    return round(sum(medias) / len(medias) / 10, 1)


async def ph(m: Ubicacion) -> float | None:
    """pH del suelo cerca de la ubicación, o None si no hay dato o el servicio no responde."""
    llave = f"{m.lat:.3f},{m.lon:.3f}"
    guardado = _cache.get(llave)
    if guardado and time.monotonic() < guardado[0]:
        return guardado[1]

    valor: float | None = None
    vigencia = SEGUNDOS_CACHE
    try:
        async with httpx.AsyncClient(timeout=20) as cliente:
            for lat, lon in _puntos(m):
                valor = await _consultar_punto(cliente, lat, lon)
                if valor is not None:
                    break
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        log.warning("SoilGrids falló para %s: %s", m.nombre, type(e).__name__)
        vigencia = SEGUNDOS_CACHE_FALLO

    _cache[llave] = (time.monotonic() + vigencia, valor)
    return valor
