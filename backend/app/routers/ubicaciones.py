"""Rutas de las ubicaciones guardadas. Sin lógica: valida la entrada y llama al servicio."""

from fastapi import APIRouter, Depends, HTTPException, Response

from app import db
from app.schemas.ubicaciones import CandidatoOut, MiUbicacionIn, UbicacionIn, UbicacionOut
from app.services import ubicaciones as servicio

router = APIRouter(prefix="/api/ubicaciones", tags=["ubicaciones"])


@router.get("", response_model=list[UbicacionOut])
def listar(con=Depends(db.con_db)):
    return [vars(u) for u in servicio.listar(con)]


# Las rutas fijas van antes que /{id} para que "buscar" y "mi-ubicacion" no se tomen por un id.
@router.get("/buscar", response_model=list[CandidatoOut])
async def buscar(q: str):
    """Busca lugares por nombre para poder agregarlos. No guarda nada."""
    try:
        return await servicio.geocodificar(q)
    except servicio.ErrorBusqueda as e:
        raise HTTPException(502, str(e))


@router.put("/mi-ubicacion", response_model=UbicacionOut)
def mi_ubicacion(datos: MiUbicacionIn, con=Depends(db.con_db)):
    """Guarda (o actualiza) "Mi ubicación" con las coordenadas que mandó el navegador."""
    return vars(servicio.guardar_mi_ubicacion(con, datos.lat, datos.lon, datos.zona))


@router.post("", response_model=UbicacionOut, status_code=201)
def crear(datos: UbicacionIn, con=Depends(db.con_db)):
    return vars(servicio.crear(con, datos.nombre, datos.lat, datos.lon, datos.zona))


@router.delete("/{ubicacion_id}", status_code=204)
def borrar(ubicacion_id: int, con=Depends(db.con_db)):
    servicio.borrar(con, ubicacion_id)
    return Response(status_code=204)
