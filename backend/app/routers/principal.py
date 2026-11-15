import asyncio
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.schemas.planificador import CultivoActivoOut
from app.services import meteomatics, municipios, soilgrids
from app.services import planificador as plan_servicio

router = APIRouter(prefix="/api/principal", tags=["principal"])

ESPERA_PH_SEGUNDOS = 4


@router.get("/clima")
async def clima(municipio: str):
    """Pronóstico de la semana (lunes a domingo) y condiciones de hoy para un municipio.

    El clima viene de Meteomatics y el pH del suelo de SoilGrids. Si SoilGrids no responde,
    el pH queda en null pero el resto de la tarjeta se muestra igual.
    """
    ciudad = municipios.buscar(municipio)
    if ciudad is None:
        raise HTTPException(404, f"Municipio desconocido: {municipio}")
    # El pH se pide en paralelo, pero no se espera de más: SoilGrids a veces tarda varios
    # segundos. Si no llega a tiempo, sigue consultando de fondo y queda en caché para la
    # siguiente vez.
    tarea_ph = asyncio.ensure_future(soilgrids.ph(ciudad))
    try:
        datos = await meteomatics.clima(ciudad)
    except meteomatics.SinCredenciales as e:
        raise HTTPException(503, str(e))
    except meteomatics.MeteomaticsError as e:
        raise HTTPException(502, str(e))
    try:
        ph = await asyncio.wait_for(asyncio.shield(tarea_ph), ESPERA_PH_SEGUNDOS)
    except asyncio.TimeoutError:
        ph = None
    # `datos` está en la caché de meteomatics: se copia en vez de modificarlo
    return {**datos, "hoy": {**datos["hoy"], "phSuelo": ph}}


@router.get("/cultivos-activos", response_model=list[CultivoActivoOut])
def cultivos_activos(
    plan_id: int | None = Query(default=None, alias="planId"),
    hoy: date | None = None,
    con=Depends(db.con_db),
):
    """Siembras en curso hoy en un plan (por defecto el primero), la que cosecha primero va primero.

    `hoy` (AAAA-MM-DD) lo manda el navegador para usar su fecha local; sin él se usa la de Monterrey.
    """
    return plan_servicio.siembras_en_curso(con, plan_id, hoy or db.hoy())
