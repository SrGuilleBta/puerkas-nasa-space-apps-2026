"""Ficha estática de cada cultivo: datos curados + rangos agronómicos de EcoCrop."""

import json
import math
import re
from pathlib import Path

import pandas as pd

from . import traduccion
from .fuentes import slug

EPPO_JSON = Path(__file__).resolve().parent / "eppo.json"
EPPO_EXTENDIDO_JSON = Path(__file__).resolve().parent / "eppo_extendido.json"


def _cargar_eppo() -> list[tuple[str, list, list]]:
    """Reglas (código, nombres, excluir) de eppo.json, con patrones de palabra completa."""
    with open(EPPO_JSON, encoding="utf-8") as f:
        codigos = json.load(f)["codigos"]
    palabra = lambda t: re.compile(rf"(?<![a-z]){re.escape(slug(t).replace('-', ' '))}(?![a-z])")
    return [(c["eppocode"], [palabra(n) for n in c["nombres"]], [palabra(n) for n in c.get("excluir", [])])
            for c in codigos]


def eppocode(nombre: str, reglas) -> str | None:
    """Código EPPO de un cultivo SIAP según su nombre (ver eppo.json)."""
    n = slug(nombre).replace("-", " ")
    for codigo, nombres, excluir in reglas:
        if any(p.search(n) for p in nombres) and not any(p.search(n) for p in excluir):
            return codigo
    return None

def _cargar_eppo_extendido() -> dict:
    with open(EPPO_EXTENDIDO_JSON, encoding="utf-8") as f:
        return json.load(f)


def _cientificos_eppo() -> dict:
    """código EPPO -> nombre científico, según las reglas de eppo.json."""
    with open(EPPO_JSON, encoding="utf-8") as f:
        return {c["eppocode"]: c["cientifico"] for c in json.load(f)["codigos"] if c.get("cientifico")}


def eppo_extendido(cid: str, tabla: dict) -> tuple[str, str] | None:
    """(código EPPO, nombre científico) por el id SIAP, con el respaldo de eppo_extendido.json.

    Orden: excepciones por id exacto, excepciones por texto contenido y después las palabras del
    id (en bloques completos: "te-limon" no coincide con "limon"). Si varias coinciden, gana la
    más larga (la más específica) y, a igual largo, la primera de la lista.
    """
    for e in tabla["excepciones_id"]:
        if cid == e["id"]:
            return e["eppocode"], e["cientifico"]
    for e in tabla["excepciones_contiene"]:
        if e["contiene"] in cid:
            return e["eppocode"], e["cientifico"]
    partes = cid.split("-")
    mejor = None
    for e in tabla["tokens"]:
        t = e["token"].split("-")
        if any(partes[i:i + len(t)] == t for i in range(len(partes) - len(t) + 1)):
            if mejor is None or len(t) > len(mejor[0]):
                mejor = (t, e)
    return (mejor[1]["eppocode"], mejor[1]["cientifico"]) if mejor else None


# EcoCrop usa nombres de familia antiguos.
FAMILIAS = {
    "Gramineae": "Poaceae", "Leguminosae": "Fabaceae", "Compositae": "Asteraceae",
    "Umbelliferae": "Apiaceae", "Cruciferae": "Brassicaceae", "Labiatae": "Lamiaceae",
    "Palmae": "Arecaceae", "Guttiferae": "Clusiaceae", "Alliaceae": "Amaryllidaceae",
}


def _num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(v) if float(v) != int(v) else int(v)


def _rango(fila, a, b, cero_es_nulo=False):
    lo, hi = _num(fila.get(a)), _num(fila.get(b))
    if lo is None or hi is None or (cero_es_nulo and (lo == 0 or hi == 0)):
        return None
    return [lo, hi]


def _consumo_agua(lluvia_opt):
    if not lluvia_opt:
        return None
    lo = lluvia_opt[0]
    return "low" if lo < 500 else "medium" if lo < 1000 else "high"


def _encharcamiento(dra):
    if not isinstance(dra, str):
        return None
    return "tolerant" if "poorly" in dra else "sensitive"


def _tipo_por_nombre(nombre: str):
    n = nombre.lower()
    if "forrajer" in n or "pasto" in n or "zacate" in n:
        return "Forraje"
    if "(gruesa)" in n or "(planta)" in n or "ornato" in n or "flor" in n:
        return "Ornamental"
    if "semilla" in n:
        return "Semilla"
    return None


def construir(nombres_cult: pd.DataFrame, curado: dict, ecocrop: pd.DataFrame,
              nacional: pd.DataFrame) -> tuple[list, dict]:
    """Devuelve (catalogo, rasgos). `rasgos` alimenta la puntuación de rotación."""
    catalogo, rasgos = [], {}
    reglas_eppo = _cargar_eppo()
    cient_eppo = _cientificos_eppo()
    tabla_ext = _cargar_eppo_extendido()
    nac = nacional.set_index("cultivo_id")
    for cid, fila_n in nombres_cult.iterrows():
        if cid not in nac.index:
            continue  # sin registros en la ventana
        nombre, unidad = fila_n["nombre"], fila_n["unidad"]
        c = curado.get(nombre, {})
        # Código EPPO y nombre científico: primero lo curado y las reglas de eppo.json; lo que falte
        # se completa con eppo_extendido.json. Así ningún cultivo reconocible queda sin código.
        codigo = eppocode(nombre, reglas_eppo)
        ext = eppo_extendido(cid, tabla_ext)  # más específico que eppo.json (p. ej. variedad de Brassica oleracea)
        cientifico = c.get("cientifico") or (ext[1] if ext else None) or cient_eppo.get(codigo)
        if ext:
            codigo = codigo or ext[0]
        sci_eco = c.get("ecocrop") or cientifico
        eco = ecocrop.loc[sci_eco].to_dict() if sci_eco in ecocrop.index else {}

        familia = c.get("familia")
        if not familia and isinstance(eco.get("FAMNAME"), str):
            f = eco["FAMNAME"].split(":")[-1]
            familia = FAMILIAS.get(f, f)

        lluvia_opt = _rango(eco, "ROPMN", "ROPMX")
        ciclo = c.get("ciclo_dias") or _rango(eco, "GMIN", "GMAX", cero_es_nulo=True)
        n = nac.loc[cid]
        ciclos = [k for k in ("PV", "OI", "PER") if n.get(f"pct_{k}", 0) > 0.02]

        entrada = {
            "id": cid,
            "nombre": traduccion.cultivo(nombre),
            "nombre_es": nombre,  # nombre SIAP en español: la búsqueda del frontend lo usa
            "eppocode": codigo,
            "unidad": traduccion.unidad(unidad),
            "tipo": traduccion.tipo(c.get("tipo") or _tipo_por_nombre(nombre)),
            "cientifico": cientifico,
            "familia": familia,
            "fija_nitrogeno": c.get("fija_nitrogeno"),
            "perenne": ciclos == ["PER"],
            "ciclos_practicados": ciclos,
            "ciclo_dias": ciclo,
            "agua": {
                "consumo": _consumo_agua(lluvia_opt),
                "lluvia_optima_mm": lluvia_opt,
                "lluvia_absoluta_mm": _rango(eco, "RMIN", "RMAX"),
            },
            "temperatura_optima_c": _rango(eco, "TOPMN", "TOPMX"),
            "temperatura_absoluta_c": _rango(eco, "TMIN", "TMAX"),
            "ph_optimo": _rango(eco, "PHOPMN", "PHOPMX"),
            "ph_absoluto": _rango(eco, "PHMIN", "PHMAX"),
            "tolerancia_encharcamiento": _encharcamiento(eco.get("DRA")),
            "altitud_max_m": _num(eco.get("ALTMX")),
            "descripcion": c.get("descripcion"),
            "suelo": c.get("suelo"),
            "cuidados": c.get("cuidados"),
            "texto_revisado": False if c.get("descripcion") else None,
            "nacional": {
                "superficie_sembrada_prom_ha": round(float(n["sembrada_prom_ha"]), 1),
                "rend_p50": None if pd.isna(n["rend_p50"]) else round(float(n["rend_p50"]), 2),
                "pmr_real_p50": None if pd.isna(n["pmr_real_p50"]) else round(float(n["pmr_real_p50"]), 0),
                "n_municipios": int(n["n_municipios"]),
            },
            "fuentes": [s for s, ok in (("SIAP", True), ("EcoCrop", bool(eco)), ("Curated", bool(c))) if ok],
        }
        catalogo.append(entrada)
        rasgos[cid] = {"familia": familia, "fija_nitrogeno": bool(c.get("fija_nitrogeno"))}

    catalogo.sort(key=lambda e: -e["nacional"]["superficie_sembrada_prom_ha"])
    return catalogo, rasgos
