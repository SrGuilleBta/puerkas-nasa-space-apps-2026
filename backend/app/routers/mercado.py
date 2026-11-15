from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.services import mercado, ubicaciones

router = APIRouter(prefix="/api/mercado", tags=["mercado"])

ESTADO = Query(..., pattern=r"^[a-z0-9_]{2,40}$", description="Estado: nombre sin acentos con guiones bajos (nuevo_leon)")


def _sin_datos(e: mercado.SinDatos):
    raise HTTPException(404, str(e))


@router.get("/estados")
def estados(municipio: str | None = None, hoy: date | None = None, con=Depends(db.con_db)):
    """Estados con precios, fecha del último dato real y, si se manda `municipio` (la ubicación activa), el estado sugerido.

    `desactualizado` avisa que el último dato real tiene más de 14 días: lo que sigue es proyección.
    """
    try:
        datos = mercado.estados(hoy or db.hoy())
    except mercado.SinDatos as e:
        _sin_datos(e)
    lugar = ubicaciones.buscar(con, municipio) if municipio else None
    return {**datos, "sugerido": mercado.clave_de_estado(lugar.cve_ent) if lugar else None}


@router.get("/productos")
def productos(estado: str = ESTADO, hoy: date | None = None):
    """Productos de un estado con su último precio, el cambio de los últimos 30 días y el proyectado a 30 días."""
    try:
        return mercado.productos(estado, hoy or db.hoy())
    except mercado.SinDatos as e:
        _sin_datos(e)


@router.get("/serie")
def serie(
    estado: str = ESTADO,
    productos: str = Query(..., description="Productos separados por comas (AGUACATE,JITOMATE); hasta 10"),
    rango: str = Query("mes", pattern="^(semana|mes|anio)$"),
    hoy: date | None = None,
):
    """Precios reales y proyección de los productos pedidos, en el rango (semana, mes o año) alrededor del último dato real."""
    ids = [p.strip() for p in productos.split(",") if p.strip()]
    if not ids:
        raise HTTPException(422, "Send at least one product")
    try:
        return mercado.serie(estado, ids, rango, hoy or db.hoy())
    except mercado.SinDatos as e:
        _sin_datos(e)
