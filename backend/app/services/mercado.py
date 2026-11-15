"""Precios de Mercado: precios al consumidor (Profeco, "Quién es Quién en los Precios") por kilo, por estado y producto.

Los archivos salen de `market_scripts/exportar_json.py` (backend/data/mercado): `meta.json` y un JSON por estado con
los precios reales (diarios los últimos 90 días y semanales antes) y una proyección. La proyección
(`market_scripts/Entrenamiento_Masivo.py`) sigue la curva estacional del producto y vuelve al nivel reciente, y le suma
variación simulada de corto plazo para que se parezca a un precio real; no usa clima, oferta ni noticias.

Son precios de venta al consumidor, no precios al productor: sirven para ver tendencias, no como precio de venta
en "Costos e ingresos" del Planificador (ahí se usa SIAP). El último dato real puede ser viejo: se avisa con
`desactualizado` y `diasSinDatos`.
"""

import json
import re
import unicodedata
from datetime import date, timedelta
from functools import lru_cache

from app.config import BASE_DIR
from app.services import estados as estados_inegi

CARPETA = BASE_DIR / "data" / "mercado"
UNIDAD = "MXN/kg"
DIAS_DATOS_VIEJOS = 14  # más viejo que esto, el último dato real se marca como desactualizado
RANGOS = {"semana": (7, 7), "mes": (30, 30), "anio": (365, None)}  # (días antes, días después) del último dato real
MAXIMO_PRODUCTOS = 10

# Productos de Profeco que no se llaman igual que su cultivo del catálogo (el resto coincide por nombre)
CULTIVO_DEL_PRODUCTO = {
    "CHAMPINON": "hongos-setas-y-champinones",
    "CHILE FRESCO": "chile-verde",
    "COL": "col-repollo",
    "GARBANZO": "garbanzo-grano",
    "HABA": "haba-grano",
    "JITOMATE": "tomate-rojo-jitomate",
    "NOPAL": "nopalitos",
    "TOMATE": "tomate-verde",  # en México "tomate" a secas es el tomate verde (tomatillo)
    "TORONJA": "toronja-pomelo",
}


class SinDatos(Exception):
    """Todavía no se generaron los datos de Mercado, o no existe ese estado o producto."""


def _slug(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_")


def _normal(texto: str) -> str:
    return " ".join(_slug(texto).split("_")).upper()


@lru_cache(maxsize=1)
def meta() -> dict:
    try:
        with open(CARPETA / "meta.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise SinDatos("The market prices have not been generated yet (python market_scripts/exportar_json.py)") from e


@lru_cache(maxsize=6)
def _estado(clave: str) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", clave or "") or clave not in {e["clave"] for e in meta()["estados"]}:
        raise SinDatos(f"No market prices for the state \"{clave}\"")
    try:
        with open(CARPETA / "estados" / f"{clave}.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise SinDatos(f"No market prices for the state \"{clave}\"") from e


def _fecha(texto: str) -> date:
    return date.fromisoformat(texto)


def _frescura(hoy: date) -> dict:
    ultimo = _fecha(meta()["ultimoDatoReal"])
    dias = (hoy - ultimo).days
    return {
        "ultimoDatoReal": meta()["ultimoDatoReal"],
        "diasSinDatos": max(0, dias),
        "desactualizado": dias > DIAS_DATOS_VIEJOS,
        "proyeccionHasta": meta()["proyeccionHasta"],
        "fuente": meta()["fuente"],
        "unidad": UNIDAD,
    }


def estados(hoy: date) -> dict:
    return {**_frescura(hoy), "estados": [{k: e[k] for k in ("clave", "nombre", "nombreEn")} for e in meta()["estados"]]}


def clave_de_estado(cve_ent: str | None) -> str | None:
    """Estado de Mercado (el nombre sin acentos con guiones bajos) a partir de la clave INEGI de una ubicación."""
    nombre = estados_inegi.ESTADOS.get(cve_ent or "")
    if not nombre:
        return None
    clave = _slug(nombre)
    return clave if clave in {e["clave"] for e in meta()["estados"]} else None


def _precio_cerca(puntos: list[list], objetivo: date, margen_dias: int) -> float | None:
    """Precio del punto más cercano a `objetivo` (hasta `margen_dias` de distancia); None si no hay."""
    mejor = min(puntos, key=lambda p: abs((_fecha(p[0]) - objetivo).days), default=None)
    if mejor is None or abs((_fecha(mejor[0]) - objetivo).days) > margen_dias:
        return None
    return mejor[1]


def _resumen(producto: str, datos: dict) -> dict:
    real, proyeccion = datos["real"], datos["proyeccion"]
    ultimo = real[-1] if real else None
    cambio = proyectado = None
    if ultimo:
        f1, p1 = _fecha(ultimo[0]), ultimo[1]
        antes = _precio_cerca(real[:-1], f1 - timedelta(days=30), 12)
        cambio = round((p1 / antes - 1) * 100, 1) if antes else None
        despues = _precio_cerca(proyeccion, f1 + timedelta(days=30), 4)
        proyectado = round((despues / p1 - 1) * 100, 1) if despues else None
    return {
        "id": producto,
        "nombre": datos["nombre"],
        "precio": ultimo[1] if ultimo else None,
        "fecha": ultimo[0] if ultimo else None,
        "cambio30dPct": cambio,
        "proyeccion30dPct": proyectado,
    }


def productos(clave: str, hoy: date) -> dict:
    """Productos de un estado con su último precio real, el cambio de los últimos 30 días y el de los 30 siguientes (proyección)."""
    d = _estado(clave)
    lista = sorted((_resumen(p, v) for p, v in d["productos"].items()), key=lambda x: x["nombre"])
    return {**_frescura(hoy), "estado": {"clave": clave, "nombre": d["estado"], "nombreEn": d["estadoEn"]}, "productos": lista}


def serie(clave: str, ids: list[str], rango: str, hoy: date) -> dict:
    """Precios reales y proyección de hasta 10 productos en un rango alrededor del último dato real.

    `rango`: "semana" (7 días antes y 7 después), "mes" (30 y 30) o "anio" (365 antes y toda la proyección). La proyección
    se une al último precio real para que las dos líneas se toquen.
    """
    if rango not in RANGOS:
        raise SinDatos(f"Unknown range \"{rango}\"")
    d = _estado(clave)
    ancla = _fecha(meta()["ultimoDatoReal"])
    antes, despues = RANGOS[rango]
    desde = ancla - timedelta(days=antes)
    hasta = _fecha(meta()["proyeccionHasta"]) if despues is None else ancla + timedelta(days=despues)

    salida = []
    for pid in list(dict.fromkeys(ids))[:MAXIMO_PRODUCTOS]:
        if pid not in d["productos"]:
            raise SinDatos(f"No market prices for \"{pid}\" in {d['estado']}")
        datos = d["productos"][pid]
        puntos: dict[str, dict] = {}
        for f, v in datos["real"]:
            if desde <= _fecha(f) <= hasta:
                puntos[f] = {"fecha": f, "real": v, "proyeccion": None}
        if datos["real"] and datos["proyeccion"]:  # la proyección arranca donde termina lo real
            f, v = datos["real"][-1]
            if f in puntos:
                puntos[f]["proyeccion"] = v
        for f, v in datos["proyeccion"]:
            if desde <= _fecha(f) <= hasta:
                puntos.setdefault(f, {"fecha": f, "real": None, "proyeccion": None})["proyeccion"] = v
        salida.append({"id": pid, "nombre": datos["nombre"], "puntos": sorted(puntos.values(), key=lambda p: p["fecha"])})
    return {**_frescura(hoy), "estado": {"clave": clave, "nombre": d["estado"], "nombreEn": d["estadoEn"]},
            "rango": rango, "desde": desde.isoformat(), "hasta": hasta.isoformat(), "productos": salida}


@lru_cache(maxsize=1)
def _producto_de_cultivo() -> dict[str, str]:
    """id del catálogo de Cultivos -> producto de Mercado. Coincide por nombre en español, más los casos de CULTIVO_DEL_PRODUCTO."""
    from app.services import cultivos

    try:
        catalogo = cultivos.catalogo()["cultivos"]
    except cultivos.SinDatos:
        return {}
    por_nombre = {_normal(c.get("nombre_es") or c["nombre"]): c["id"] for c in catalogo}
    ids = {c["id"] for c in catalogo}
    mapa = {}
    for producto in meta()["productos"]:
        cultivo = CULTIVO_DEL_PRODUCTO.get(producto) or por_nombre.get(_normal(producto))
        if cultivo in ids:
            mapa.setdefault(cultivo, producto)
    return mapa


def producto_de_cultivo(catalogo_id: str | None) -> str | None:
    if not catalogo_id:
        return None
    try:
        return _producto_de_cultivo().get(catalogo_id)
    except SinDatos:
        return None


def tendencia(catalogo_id: str | None, clave_estado: str | None, hoy: date) -> dict | None:
    """Último precio al consumidor y su tendencia para un cultivo del catálogo en un estado; None si no hay producto o datos."""
    producto = producto_de_cultivo(catalogo_id)
    if producto is None:
        return None
    try:
        d = _estado(clave_estado) if clave_estado else None
    except SinDatos:
        d = None
    if d is None or producto not in d["productos"]:
        return None
    r = _resumen(producto, d["productos"][producto])
    if r["precio"] is None:
        return None
    return {**r, "producto": producto, "estado": d["estado"], **{k: v for k, v in _frescura(hoy).items() if k in ("desactualizado", "diasSinDatos", "unidad", "fuente")}}
