import asyncio

from fastapi import APIRouter, HTTPException

from app.services import meteomatics, municipios, soilgrids

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
