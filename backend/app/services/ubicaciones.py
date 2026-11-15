"""Lugares para los que se consulta el clima y el suelo (ubicaciones guardadas en la base).

Hay 4 ciudades de inicio; el usuario puede agregar más (buscándolas por nombre) y guardar su
ubicación actual como "Mi ubicación". No conoce FastAPI: los errores son los mismos del
Planificador y el router los traduce a respuestas HTTP.
"""

import sqlite3
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.db import clave
from app.services.planificador import Conflicto, Invalido, NoEncontrado

NOMBRE_MI_UBICACION = "Mi ubicación"
URL_BUSQUEDA = "https://geocoding-api.open-meteo.com/v1/search"
PAIS = "MX"  # la búsqueda de lugares se limita a México


@dataclass(frozen=True)
class Ubicacion:
    id: int
    nombre: str
    lat: float
    lon: float
    zona: str  # zona horaria IANA
    # Campo agrícola cercano para consultar el suelo. Solo lo traen las ciudades de inicio;
    # en las demás el suelo busca un punto con dato cerca de (lat, lon).
    lat_suelo: float | None = None
    lon_suelo: float | None = None


class ErrorBusqueda(Exception):
    """No se pudo consultar el servicio que busca lugares por nombre."""


def _desde_fila(f: sqlite3.Row) -> Ubicacion:
    return Ubicacion(f["id"], f["nombre"], f["lat"], f["lon"], f["zona"], f["lat_suelo"], f["lon_suelo"])


def listar(con) -> list[Ubicacion]:
    return [_desde_fila(f) for f in con.execute("SELECT * FROM ubicacion ORDER BY id")]


def buscar(con, nombre: str) -> Ubicacion | None:
    f = con.execute("SELECT * FROM ubicacion WHERE clave = ?", (clave(nombre),)).fetchone()
    return _desde_fila(f) if f else None


def _validar(nombre: str, lat: float, lon: float, zona: str) -> str:
    nombre = " ".join(nombre.split())
    if not nombre:
        raise Invalido("Escribe el nombre del lugar")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise Invalido("Las coordenadas no son válidas")
    try:
        ZoneInfo(zona)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise Invalido(f"La zona horaria «{zona}» no existe")
    return nombre


def crear(con, nombre: str, lat: float, lon: float, zona: str) -> Ubicacion:
    nombre = _validar(nombre, lat, lon, zona)
    existente = buscar(con, nombre)
    if existente:
        raise Conflicto(f"Ya tienes guardado «{existente.nombre}»")
    with con:
        id_ = con.execute(
            "INSERT INTO ubicacion (nombre, clave, lat, lon, zona) VALUES (?, ?, ?, ?, ?)",
            (nombre, clave(nombre), lat, lon, zona),
        ).lastrowid
    return buscar_por_id(con, id_)


def guardar_mi_ubicacion(con, lat: float, lon: float, zona: str) -> Ubicacion:
    """Crea o actualiza "Mi ubicación" con las coordenadas del navegador. Siempre es una sola."""
    nombre = _validar(NOMBRE_MI_UBICACION, lat, lon, zona)
    with con:
        con.execute(
            "INSERT INTO ubicacion (nombre, clave, lat, lon, zona) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET lat = excluded.lat, lon = excluded.lon, zona = excluded.zona",
            (nombre, clave(nombre), lat, lon, zona),
        )
    return buscar(con, nombre)


def buscar_por_id(con, id_: int) -> Ubicacion:
    f = con.execute("SELECT * FROM ubicacion WHERE id = ?", (id_,)).fetchone()
    if f is None:
        raise NoEncontrado(f"No existe la ubicación con id {id_}")
    return _desde_fila(f)


def borrar(con, id_: int) -> None:
    buscar_por_id(con, id_)
    if con.execute("SELECT COUNT(*) FROM ubicacion").fetchone()[0] <= 1:
        raise Conflicto("Debe quedar al menos una ubicación")
    with con:
        con.execute("DELETE FROM ubicacion WHERE id = ?", (id_,))


async def geocodificar(texto: str) -> list[dict]:
    """Busca lugares por nombre (servicio gratuito de Open-Meteo, sin llave).

    Solo se envía el texto que el usuario escribió para buscar. Solo se buscan lugares de México
    (el clima, el suelo y el catálogo de cultivos están pensados para el campo mexicano). Devuelve
    hasta 6 candidatos con nombre completo ("Guadalajara, Jalisco, México"), coordenadas y zona horaria.
    """
    texto = " ".join(texto.split())
    if len(texto) < 2:
        raise Invalido("Escribe al menos 2 letras para buscar")
    try:
        async with httpx.AsyncClient(timeout=10) as cliente:
            r = await cliente.get(
                URL_BUSQUEDA,
                params={"name": texto, "count": 6, "language": "es", "format": "json", "countryCode": PAIS},
            )
            r.raise_for_status()
        resultados = r.json().get("results") or []
    except (httpx.HTTPError, ValueError) as e:
        raise ErrorBusqueda(f"No se pudo buscar el lugar ({type(e).__name__})") from e

    candidatos = []
    for x in resultados:
        if x.get("country_code") != PAIS:  # por si el servicio devolviera algo de otro país
            continue
        partes = [x.get("name"), x.get("admin1"), x.get("country")]
        nombre = ", ".join(dict.fromkeys(p for p in partes if p))  # sin repetir (p. ej. ciudad = estado)
        if x.get("timezone") and nombre:
            candidatos.append(
                {"nombre": nombre, "lat": x["latitude"], "lon": x["longitude"], "zona": x["timezone"]}
            )
    return candidatos
