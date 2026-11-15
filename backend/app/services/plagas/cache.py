"""Caché en disco del motor de plagas.

Las respuestas de EPPO casi no cambian (nombres, hospederos, control biológico) y consultarlas es lento y
tiene límite de uso, así que se guardan en `backend/data/plagas/cache` (no se sube a git). Cada archivo
lleva la fecha en que se guardó y se descarta cuando pasa su vigencia. Se puede cambiar la carpeta con
PLAGAS_CACHE (por ejemplo en las pruebas).
"""

import json
import os
import re
import time
from pathlib import Path

from app.config import BASE_DIR

CARPETA = Path(os.environ.get("PLAGAS_CACHE") or BASE_DIR / "data" / "plagas" / "cache")
DIA = 86400


def _ruta(categoria: str, clave: str) -> Path:
    segura = re.sub(r"[^A-Za-z0-9._-]+", "_", clave)[:120]  # la clave viene de códigos EPPO y coordenadas
    return CARPETA / categoria / f"{segura}.json"


def leer(categoria: str, clave: str, vigencia_dias: float):
    """Lo guardado, o None si no hay, venció o el archivo está dañado."""
    ruta = _ruta(categoria, clave)
    try:
        with open(ruta, encoding="utf-8") as f:
            guardado = json.load(f)
        if time.time() - guardado["guardado"] > vigencia_dias * DIA:
            return None
        return guardado["datos"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def escribir(categoria: str, clave: str, datos) -> None:
    """Guarda `datos`; si el disco falla, el motor sigue funcionando sin caché."""
    ruta = _ruta(categoria, clave)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_suffix(".tmp")
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump({"guardado": time.time(), "datos": datos}, f, ensure_ascii=False)
        os.replace(temporal, ruta)  # así nunca queda un archivo a medias
    except OSError:
        pass
