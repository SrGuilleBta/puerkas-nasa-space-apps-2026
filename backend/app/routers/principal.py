from fastapi import APIRouter, HTTPException

from app.services import meteomatics, municipios

router = APIRouter(prefix="/api/principal", tags=["principal"])


@router.get("/clima")
async def clima(municipio: str):
    """Pronóstico de la semana (lunes a domingo) y condiciones de hoy para un municipio."""
    ciudad = municipios.buscar(municipio)
    if ciudad is None:
        raise HTTPException(404, f"Municipio desconocido: {municipio}")
    try:
        return await meteomatics.clima(ciudad)
    except meteomatics.SinCredenciales as e:
        raise HTTPException(503, str(e))
    except meteomatics.MeteomaticsError as e:
        raise HTTPException(502, str(e))
