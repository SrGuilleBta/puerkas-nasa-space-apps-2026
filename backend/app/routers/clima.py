from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.services import mapa_clima, ubicaciones

router = APIRouter(prefix="/api/clima", tags=["clima"])


@router.get("/mapa")
async def mapa(con=Depends(db.con_db)):
    """Pronóstico de 7 días de lluvia (mm) y temperatura máxima (°C) sobre México, en una malla de puntos, más el
    contorno del país y los lugares guardados. Con caché de 3 horas; ver `services/mapa_clima.py`."""
    lugares = [(u.nombre, u.lat, u.lon) for u in ubicaciones.listar(con)]
    try:
        return await mapa_clima.mapa(lugares)
    except mapa_clima.ErrorMapaClima as e:
        raise HTTPException(502, str(e))
