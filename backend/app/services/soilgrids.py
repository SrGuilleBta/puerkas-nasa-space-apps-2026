"""pH del suelo con SoilGrids (https://rest.isric.org). No necesita llave.

El suelo casi no cambia, así que el resultado se guarda 24 horas; SoilGrids limita las
consultas (unas 5 por minuto) y es lento. Si falla, se devuelve None en vez de romper la
pantalla, y no se vuelve a intentar durante unos minutos.
"""

import logging
import time

import httpx

from app.services.municipios import Municipio

log = logging.getLogger(__name__)

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROFUNDIDADES = ["0-5cm", "5-15cm", "15-30cm"]  # zona de raíces
SEGUNDOS_CACHE = 24 * 3600
SEGUNDOS_CACHE_FALLO = 300

_cache: dict[str, tuple[float, float | None]] = {}


async def ph(m: Municipio) -> float | None:
    """pH promedio de los primeros 30 cm del campo cercano al municipio, o None si no hay dato."""
    guardado = _cache.get(m.nombre)
    if guardado and time.monotonic() < guardado[0]:
        return guardado[1]

    params = [
        ("lon", m.lon_suelo),
        ("lat", m.lat_suelo),
        ("property", "phh2o"),
        ("value", "mean"),
        *[("depth", p) for p in PROFUNDIDADES],
    ]
    valor: float | None = None
    vigencia = SEGUNDOS_CACHE
    try:
        async with httpx.AsyncClient(timeout=20) as cliente:
            r = await cliente.get(URL, params=params)
            r.raise_for_status()
        profundidades = r.json()["properties"]["layers"][0]["depths"]
        medias = [d["values"]["mean"] for d in profundidades if d["values"]["mean"] is not None]
        if medias:
            # SoilGrids guarda el pH multiplicado por 10 (77 significa pH 7.7)
            valor = round(sum(medias) / len(medias) / 10, 1)
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        log.warning("SoilGrids falló para %s: %s", m.nombre, type(e).__name__)
        vigencia = SEGUNDOS_CACHE_FALLO

    _cache[m.nombre] = (time.monotonic() + vigencia, valor)
    return valor
