import os


def _variable(nombre: str) -> str:
    # strip(): es fácil que al pegar la llave en .env quede un espacio o salto de línea al final
    return os.environ.get(nombre, "").strip()


METEOMATICS_USER = _variable("METEOMATICS_USER")
METEOMATICS_PASSWORD = _variable("METEOMATICS_PASSWORD")
