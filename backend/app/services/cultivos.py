"""Lee los JSON precalculados por la pipeline (backend/pipeline/cultivos).

No calcula nada: solo carga archivos y junta la ficha del catálogo con los
indicadores de la ubicación. Si falta un dato en el municipio, cae al estado y
luego al nivel nacional.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATOS = Path(__file__).resolve().parents[2] / "data" / "cultivos"


def _normal(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


class SinDatos(Exception):
    """La pipeline no se ha corrido o la clave no existe."""


def _leer(ruta: Path) -> dict:
    if not ruta.exists():
        raise SinDatos(str(ruta.relative_to(DATOS.parent)))
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def catalogo() -> dict:
    datos = _leer(DATOS / "catalogo.json")
    datos["por_id"] = {c["id"]: c for c in datos["cultivos"]}
    return datos


@lru_cache(maxsize=1)
def ubicaciones() -> dict:
    return _leer(DATOS / "ubicaciones.json")


@lru_cache(maxsize=1)
def _indice_ubicaciones() -> dict:
    """clave -> descriptor de ubicación, para todas las claves válidas (con o sin datos)."""
    idx = {"00": {"nivel": "nacional", "clave": "00", "nombre": "México"}}
    for e in ubicaciones()["estados"]:
        idx[e["clave"]] = {"nivel": "estado", "clave": e["clave"], "nombre": e["nombre"]}
        for m in e["municipios"]:
            idx[m["clave"]] = {"nivel": "municipio", "clave": m["clave"], "nombre": m["nombre"],
                               "cve_ent": e["clave"], "estado": e["nombre"]}
    return idx


@lru_cache(maxsize=1)
def meta() -> dict:
    return _leer(DATOS / "meta.json")


@lru_cache(maxsize=512)
def ubicacion(clave: str) -> dict:
    """clave: '00' (nacional), 2 dígitos (estado) o 5 dígitos (municipio, CVEGEO)."""
    if clave == "00":
        return _leer(DATOS / "nacional.json")
    if len(clave) == 2:
        return _leer(DATOS / "estados" / f"{clave}.json")
    if len(clave) == 5:
        return _leer(DATOS / "municipios" / f"{clave}.json")
    raise SinDatos(clave)


def _buscar(clave: str, cultivo: str):
    try:
        datos = ubicacion(clave)
    except SinDatos:
        return None, None
    for c in datos["cultivos"]:
        if c["id"] == cultivo:
            return datos, c
    return datos, None


def viabilidad(clave: str, cultivo: str) -> dict:
    """Ficha completa de un cultivo en una ubicación.

    `nivel_datos` indica de dónde salieron los indicadores: si el municipio no
    siembra el cultivo, se devuelven los del estado (o los nacionales) y
    `sembrado_en_ubicacion` es False.
    """
    ficha = catalogo()["por_id"].get(cultivo)
    if ficha is None:
        raise SinDatos(f"cultivo {cultivo}")
    descriptor = _indice_ubicaciones().get(clave)
    if descriptor is None:
        raise SinDatos(f"ubicación {clave}")

    cadena = [clave]
    if len(clave) == 5:
        cadena.append(clave[:2])
    if clave != "00":
        cadena.append("00")

    # Un municipio sin registros agrícolas en SIAP (p. ej. Monterrey) no tiene archivo:
    # se responde igual, con contexto vacío y los indicadores del estado.
    pedida, _ = _buscar(clave, cultivo)
    indicadores, origen = None, None
    for k in cadena:
        datos, ind = _buscar(k, cultivo)
        if ind is not None:
            indicadores, origen = ind, datos["ubicacion"]
            break

    enchar = ficha.get("tolerancia_encharcamiento")
    return {
        "ubicacion": descriptor,
        "contexto": pedida["contexto"] if pedida else None,
        "ventana": catalogo()["ventana"],
        "ficha": {k: v for k, v in ficha.items() if k != "nacional"},
        "nacional": ficha.get("nacional"),
        "sembrado_en_ubicacion": origen is not None and origen["clave"] == clave,
        "nivel_datos": origen["nivel"] if origen else None,
        "ubicacion_datos": origen,
        "indicadores": indicadores,
        "sensibilidad_inundacion": {
            "nivel": {"tolera": "baja", "sensible": "alta"}.get(enchar),
            "fuente": "EcoCrop (tolerancia a mal drenaje)",
            "pendiente": "Atlas Nacional de Riesgos (CENAPRED)",
        },
    }


def biblioteca(clave: str | None = None, buscar: str | None = None) -> list[dict]:
    """Lista ligera para la barra lateral. Con `clave`, ordena por superficie en esa
    ubicación y marca qué cultivos se siembran ahí."""
    cat = catalogo()["cultivos"]
    locales = {}
    if clave:
        if clave not in _indice_ubicaciones():
            raise SinDatos(f"ubicación {clave}")
        try:
            locales = {c["id"]: c for c in ubicacion(clave)["cultivos"]}
        except SinDatos:
            pass  # municipio válido sin registros agrícolas: catálogo completo sin marcar
    filas = []
    for c in cat:
        if buscar and _normal(buscar) not in _normal(c["nombre"]):
            continue
        loc = locales.get(c["id"])
        filas.append({
            "id": c["id"], "nombre": c["nombre"], "tipo": c.get("tipo"),
            "ciclo_dias": c.get("ciclo_dias"), "perenne": c.get("perenne"),
            "sembrado_en_ubicacion": loc is not None,
            "superficie_local_ha": loc["superficie_sembrada_prom_ha"] if loc else None,
        })
    if clave:
        filas.sort(key=lambda f: -(f["superficie_local_ha"] or 0))
    return filas
