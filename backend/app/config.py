import os
from pathlib import Path


def _variable(nombre: str) -> str:
    # strip(): es fácil que al pegar la llave en .env quede un espacio o salto de línea al final
    return os.environ.get(nombre, "").strip()


METEOMATICS_USER = _variable("METEOMATICS_USER")
METEOMATICS_PASSWORD = _variable("METEOMATICS_PASSWORD")

# Motor de plagas: llave de EPPO (sin ella no hay análisis por cultivo y las alertas usan reglas generales)
EPPO_API_KEY = _variable("EPPO_API_KEY")

# Base de datos del Planificador (SQLite). Vive en backend/data, que se comparte con el
# contenedor, y no se sube a git. Se puede cambiar con PLANIFICADOR_DB (por ejemplo en pruebas).
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("PLANIFICADOR_DB") or BASE_DIR / "data" / "planificador.db")
