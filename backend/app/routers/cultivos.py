from fastapi import APIRouter, HTTPException, Query

from app.services import cultivos

router = APIRouter(prefix="/api/cultivos", tags=["cultivos"])

CLAVE = Query(..., pattern=r"^(\d{2}|\d{5})$",
              description="'00' nacional, 2 dígitos estado o 5 dígitos municipio (CVEGEO INEGI)")


def _no_encontrado(e: cultivos.SinDatos):
    raise HTTPException(404, f"No data: {e}. Has the pipeline been run? (python -m pipeline.cultivos)")


@router.get("/catalogo")
def catalogo():
    """Ficha estática de todos los cultivos (EcoCrop + curado + resumen nacional)."""
    try:
        c = cultivos.catalogo()
    except cultivos.SinDatos as e:
        _no_encontrado(e)
    return {"ventana": c["ventana"], "cultivos": c["cultivos"]}


@router.get("/biblioteca")
def biblioteca(clave: str | None = Query(None, pattern=r"^(\d{2}|\d{5})$"), buscar: str | None = None):
    """Lista ligera para el buscador; con `clave` se ordena por lo que se siembra ahí."""
    try:
        return cultivos.biblioteca(clave, buscar)
    except cultivos.SinDatos as e:
        _no_encontrado(e)


@router.get("/ubicaciones")
def ubicaciones():
    """Estados y municipios para el selector."""
    try:
        return cultivos.ubicaciones()
    except cultivos.SinDatos as e:
        _no_encontrado(e)


@router.get("/ubicacion")
def ubicacion(clave: str = CLAVE):
    """Todos los cultivos con indicadores en una ubicación."""
    try:
        return cultivos.ubicacion(clave)
    except cultivos.SinDatos as e:
        _no_encontrado(e)


@router.get("/viabilidad")
def viabilidad(clave: str = CLAVE, cultivo: str = Query(..., description="id del catálogo, p. ej. maiz-grano")):
    """Ficha + indicadores de un cultivo en una ubicación (con respaldo estado/nación)."""
    try:
        return cultivos.viabilidad(clave, cultivo)
    except cultivos.SinDatos as e:
        _no_encontrado(e)


@router.get("/meta")
def meta():
    """Fecha de generación, ventana de años y fuentes usadas."""
    try:
        return cultivos.meta()
    except cultivos.SinDatos as e:
        _no_encontrado(e)
