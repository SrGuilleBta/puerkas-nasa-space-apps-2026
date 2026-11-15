"""Ficha estática de cada cultivo: datos curados + rangos agronómicos de EcoCrop."""

import math

import pandas as pd

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
    return "bajo" if lo < 500 else "medio" if lo < 1000 else "alto"


def _encharcamiento(dra):
    if not isinstance(dra, str):
        return None
    return "tolera" if "poorly" in dra else "sensible"


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
    nac = nacional.set_index("cultivo_id")
    for cid, fila_n in nombres_cult.iterrows():
        if cid not in nac.index:
            continue  # sin registros en la ventana
        nombre, unidad = fila_n["nombre"], fila_n["unidad"]
        c = curado.get(nombre, {})
        sci_eco = c.get("ecocrop") or c.get("cientifico")
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
            "nombre": nombre,
            "unidad": unidad,
            "tipo": c.get("tipo") or _tipo_por_nombre(nombre),
            "cientifico": c.get("cientifico"),
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
            "fuentes": [s for s, ok in (("SIAP", True), ("EcoCrop", bool(eco)), ("Curado", bool(c))) if ok],
        }
        catalogo.append(entrada)
        rasgos[cid] = {"familia": familia, "fija_nitrogeno": bool(c.get("fija_nitrogeno"))}

    catalogo.sort(key=lambda e: -e["nacional"]["superficie_sembrada_prom_ha"])
    return catalogo, rasgos
