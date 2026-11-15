"""Datos de FAO EcoCrop que el catálogo de Cultivos todavía no trae: la textura de suelo de cada cultivo.

Lee `backend/data/ecocrop/EcoCrop_DB.csv` (el mismo archivo que usa la pipeline) y cruza por nombre
científico, igual que ella (si hay filas repetidas, gana la primera). EcoCrop describe la textura con
clases amplias: `light` (suelos arenosos), `medium` (francos) y `heavy` (arcillosos), más `organic` y
`wide` (crece en cualquier textura). No hay una equivalencia oficial entre esas clases y las del USDA que
usa el módulo Suelo, así que aquí solo se entregan las clases tal como las trae EcoCrop.

Limitación: los 7 cultivos que la pipeline cruza con otro nombre (`ecocrop` en curado.json, p. ej. el jitomate)
no coinciden aquí y quedan sin textura.
"""

import csv
from functools import lru_cache
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "data" / "ecocrop" / "EcoCrop_DB.csv"
CLASES = {"light", "medium", "heavy", "wide", "organic"}


def _clases(texto: str | None) -> list[str]:
    """'heavy, medium' -> ['heavy', 'medium']; descarta lo vacío y lo que no sea una clase conocida."""
    return [p for p in (x.strip() for x in (texto or "").split(",")) if p in CLASES]


@lru_cache(maxsize=1)
def _tabla() -> dict[str, dict]:
    if not CSV.exists():
        return {}
    tabla: dict[str, dict] = {}
    with open(CSV, encoding="latin1", newline="") as f:
        for fila in csv.DictReader(f):
            nombre = fila.get("ScientificName")
            if nombre and nombre not in tabla:
                tabla[nombre] = {"optima": _clases(fila.get("TEXT")), "tolerada": _clases(fila.get("TEXTR"))}
    return tabla


def textura(cientifico: str | None) -> dict | None:
    """Texturas de suelo de un cultivo: {"optima": [...], "tolerada": [...]} con clases de EcoCrop.
    None si el cultivo no está en EcoCrop o EcoCrop no trae su textura."""
    t = _tabla().get(cientifico or "")
    return t if t and (t["optima"] or t["tolerada"]) else None
