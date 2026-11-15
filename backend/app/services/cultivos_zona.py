"""Zona de SIAP (municipio o estado) que corresponde a una ubicación del proyecto.

Las ubicaciones (`app/services/ubicaciones.py`) solo guardan nombre y coordenadas; la enciclopedia
de cultivos trabaja con claves INEGI (estado de 2 dígitos, municipio de 5). Aquí se hace el puente:
1. Por nombre: "Monterrey, NL", "Guadalajara, Jalisco, Mexico" -> estado + municipio.
2. Por coordenadas (p. ej. "My location", que no trae lugar): geocodificación inversa con
   Nominatim (OpenStreetMap), que devuelve estado y municipio.
Si hay municipio con ese nombre dentro del estado se devuelve; si no, solo el estado; si ni eso, None.
"""

import unicodedata
from functools import lru_cache

import httpx

from app.services import cultivos

URL_INVERSA = "https://nominatim.openstreetmap.org/reverse"
AGENTE = "cropro-app/1.0"

# Abreviaturas y nombres en inglés que usan las ubicaciones iniciales y el geocodificador
ALIAS_ESTADOS = {
    "ags": "01", "bc": "02", "bcs": "03", "camp": "04", "coah": "05", "col": "06", "chis": "07",
    "chih": "08", "cdmx": "09", "mexico city": "09", "distrito federal": "09", "dgo": "10",
    "gto": "11", "gro": "12", "hgo": "13", "jal": "14", "state of mexico": "15", "estado de mexico": "15",
    "edomex": "15", "mex": "15", "mich": "16", "mor": "17", "nay": "18", "nl": "19", "oax": "20",
    "pue": "21", "qro": "22", "q roo": "23", "qroo": "23", "slp": "24", "sin": "25", "son": "26",
    "tab": "27", "tamps": "28", "tlax": "29", "ver": "30", "yuc": "31", "zac": "32",
}
PAISES = {"mexico", "mx"}


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return " ".join("".join(c if c.isalnum() else " " for c in t).split())


@lru_cache(maxsize=1)
def _indices() -> tuple[dict, dict]:
    """(nombre normalizado -> clave de estado, (clave de estado, nombre normalizado) -> clave de municipio)."""
    estados, municipios = dict(ALIAS_ESTADOS), {}
    for e in cultivos.ubicaciones()["estados"]:
        estados.setdefault(_norm(e["nombre"]), e["clave"])
        for m in e["municipios"]:
            municipios.setdefault((e["clave"], _norm(m["nombre"])), m["clave"])
    # "Mexico" solo es el Estado de México si no es el país
    estados["mexico"] = "15"
    return estados, municipios


def _resolver(estado: str | None, municipio: str | None) -> dict | None:
    estados, municipios = _indices()
    cve_ent = estados.get(_norm(estado or ""))
    if cve_ent is None:
        return None
    cve_mun = municipios.get((cve_ent, _norm(municipio or ""))) if municipio else None
    return _respuesta(cve_mun or cve_ent)


def _respuesta(clave: str) -> dict:
    d = cultivos._indice_ubicaciones()[clave]
    return {"clave": clave, "nivel": d["nivel"], "nombre": d["nombre"], "estado": d.get("estado", d["nombre"]),
            "cve_ent": d.get("cve_ent", clave)}


def desde_nombre(nombre: str) -> dict | None:
    """'Monterrey, NL' / 'Guadalajara, Jalisco, Mexico' -> zona; None si no se reconoce el estado."""
    partes = [p.strip() for p in (nombre or "").split(",") if p.strip()]
    if partes and _norm(partes[-1]) in PAISES and len(partes) > 1:
        partes = partes[:-1]
    if len(partes) >= 2:
        return _resolver(partes[-1], partes[0])
    return None


async def desde_coordenadas(lat: float, lon: float) -> dict | None:
    """Geocodificación inversa (solo se envían las coordenadas). None si falla o no es México."""
    try:
        async with httpx.AsyncClient(timeout=8, headers={"User-Agent": AGENTE}) as c:
            r = await c.get(URL_INVERSA, params={"format": "jsonv2", "zoom": 10, "accept-language": "es",
                                                 "lat": lat, "lon": lon})
            r.raise_for_status()
        dir_ = r.json().get("address") or {}
    except (httpx.HTTPError, ValueError):
        return None
    if dir_.get("country_code") != "mx":
        return None
    return _resolver(dir_.get("state"), dir_.get("county") or dir_.get("municipality") or dir_.get("city"))


async def resolver(nombre: str | None, lat: float | None, lon: float | None) -> dict | None:
    zona = desde_nombre(nombre) if nombre else None
    if zona is None and lat is not None and lon is not None:
        zona = await desde_coordenadas(lat, lon)
    return zona
