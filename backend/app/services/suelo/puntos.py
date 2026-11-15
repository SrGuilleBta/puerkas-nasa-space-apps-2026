"""Puntos de suelo de las ubicaciones guardadas (tabla `ubicacion`, ver app/db.py), para los scripts
de precarga."""

from dataclasses import dataclass

from app import db
from app.services import ubicaciones
from app.services.suelo import modis


@dataclass(frozen=True)
class PuntoSuelo:
    nombre: str
    lat_suelo: float
    lon_suelo: float


async def de_ubicaciones() -> list[PuntoSuelo]:
    """Un punto por ubicación: el píxel de cultivo más cercano (MODIS), igual que la API de Suelo."""
    db.iniciar()
    con = db.conectar()
    try:
        lista = ubicaciones.listar(con)
    finally:
        con.close()
    puntos = []
    for u in lista:  # misma regla que la API: siempre el cultivo más cercano (no se usa lat_suelo)
        try:
            c = await modis.cultivo_cercano(u.lat, u.lon)
        except Exception:  # noqa: BLE001
            c = None
        puntos.append(PuntoSuelo(u.nombre, c["lat"], c["lon"]) if c else PuntoSuelo(u.nombre, u.lat, u.lon))
    return puntos
