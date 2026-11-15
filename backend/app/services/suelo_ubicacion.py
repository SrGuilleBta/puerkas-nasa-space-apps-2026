"""Datos de suelo de una ubicación guardada, para Principal y las alertas.

Usa el módulo Suelo (services/suelo) con el mismo punto que la pantalla Soil: el píxel de cultivo más
cercano según MODIS, o el lugar mismo si no hay. Así los números de Principal coinciden con los de Soil.
"""

from app.services.suelo import modis, smap, soilgrids
from app.services.suelo import nasa_power as suelo_power


async def punto(ciudad) -> tuple[float, float]:
    try:
        c = await modis.cultivo_cercano(ciudad.lat, ciudad.lon)
    except Exception:  # noqa: BLE001 - sin MODIS se usa el lugar mismo
        c = None
    return (c["lat"], c["lon"]) if c else (ciudad.lat, ciudad.lon)


async def ph(ciudad) -> float | None:
    """pH de la capa superficial (0-5 cm), o None si SoilGrids no responde."""
    try:
        lat, lon = await punto(ciudad)
        datos = await soilgrids.propiedades(lat, lon, ciudad.nombre)
        capas = [] if datos.get("sin_datos") else datos.get("capas", [])
        return capas[0]["ph"] if capas else None
    except Exception:  # noqa: BLE001 - el pH es opcional en la tarjeta
        return None


async def humedad_raiz(ciudad) -> float | None:
    """Humedad de la zona de raíz de hoy (NASA POWER, %), la misma cifra que muestra la pantalla Soil."""
    try:
        lat, lon = await punto(ciudad)
        dato = await suelo_power.actual(lat, lon)
        return dato["humedad_raiz"] if dato else None
    except Exception:  # noqa: BLE001
        return None


async def humedad_vs_normal(ciudad) -> dict | None:
    """Humedad de los últimos 30 días medida por SMAP contra otros años (percentil), o None."""
    try:
        lat, lon = await punto(ciudad)
        datos = await smap.estado_sequia(lat, lon)
    except Exception:  # noqa: BLE001
        return None
    if not datos or datos.get("mensaje") or datos.get("percentil") is None:
        return None
    return {"percentil": datos["percentil"], "categoria": datos["categoria"], "humedad": datos["humedad_promedio"],
            "normal": datos["promedio_historico_periodo"]}
