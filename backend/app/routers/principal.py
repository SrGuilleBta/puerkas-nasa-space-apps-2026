import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.schemas.planificador import CultivoActivoOut
from app.services import alertas, catalogo_cultivos, meteomatics, nasa_power, soilgrids, ubicaciones
from app.services import planificador as plan_servicio

router = APIRouter(prefix="/api/principal", tags=["principal"])

ESPERA_PH_SEGUNDOS = 4


@router.get("/clima")
async def clima(municipio: str, con=Depends(db.con_db)):
    """Pronóstico de la semana (lunes a domingo) y condiciones de hoy para una ubicación guardada.

    `municipio` es el nombre de la ubicación (ver /api/ubicaciones). El clima viene de Meteomatics
    y el pH del suelo de SoilGrids. Si SoilGrids no responde, el pH queda en null pero el resto de
    la tarjeta se muestra igual.
    """
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
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


@router.get("/clima-nasa")
async def clima_nasa(municipio: str, desde: date, hasta: date, con=Depends(db.con_db)):
    """Lo que pasó en el campo en un periodo (lluvia, temperatura, radiación, humedad de la raíz), de NASA POWER."""
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
    try:
        return await nasa_power.periodo(ciudad.lat, ciudad.lon, desde, hasta)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except nasa_power.ErrorNasaPower as e:
        raise HTTPException(502, str(e))


@router.get("/alertas")
async def alertas_del_dia(
    municipio: str,
    plan_id: int | None = Query(default=None, alias="planId"),
    hoy: date | None = None,
    con=Depends(db.con_db),
):
    """Riesgos del clima y condiciones favorables para plagas, según el pronóstico y los cultivos en curso.

    Son avisos para revisar el campo, no detecciones. Si no hay riesgos devuelve una lista vacía.
    """
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
    try:
        datos = await meteomatics.clima(ciudad)  # misma caché que /clima: no gasta otra consulta
    except meteomatics.SinCredenciales as e:
        raise HTTPException(503, str(e))
    except meteomatics.MeteomaticsError as e:
        raise HTTPException(502, str(e))
    dia = hoy or db.hoy()
    activos = plan_servicio.siembras_en_curso(con, plan_id, dia)
    try:  # sin esta lluvia solo faltan las alertas de sequía: el resto se calcula igual
        reciente = await nasa_power.periodo(ciudad.lat, ciudad.lon, dia - timedelta(days=30), dia)
    except nasa_power.ErrorNasaPower:
        reciente = None
    return alertas.calcular(datos, activos, dia, catalogo_cultivos.fichas_de(activos), reciente)


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
