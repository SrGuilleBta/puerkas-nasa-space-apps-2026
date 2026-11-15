import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.schemas.planificador import CultivoActivoOut, TareasVencidasOut
from app.services import alertas, catalogo_cultivos, nasa_power, suelo_ubicacion, tareas, ubicaciones
from app.services import clima as clima_servicio
from app.services import planificador as plan_servicio
from app.services import plagas as motor_plagas

router = APIRouter(prefix="/api/principal", tags=["principal"])

ESPERA_SUELO_SEGUNDOS = 6


@router.get("/clima")
async def clima(municipio: str, con=Depends(db.con_db)):
    """Pronóstico de 7 días (hoy y los 6 siguientes) y condiciones de hoy para una ubicación guardada.

    `municipio` es el nombre de la ubicación (ver /api/ubicaciones). El clima viene de Meteomatics y,
    si no hay llaves o no responde, de Open-Meteo (`fuente` dice cuál); el pH y la humedad del suelo, del módulo Suelo (SoilGrids y NASA POWER), con el mismo punto que la
    pantalla Soil. Si el suelo no responde a tiempo, esos datos quedan como estaban (humedad de
    Meteomatics) o en null (pH) y el resto de la tarjeta se muestra igual.
    """
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
    # El suelo se pide en paralelo, pero no se espera de más: a veces tarda varios segundos. Si no llega
    # a tiempo, sigue consultando de fondo y queda en caché para la siguiente vez.
    tarea_ph = asyncio.ensure_future(suelo_ubicacion.ph(ciudad))
    tarea_humedad = asyncio.ensure_future(suelo_ubicacion.humedad_raiz(ciudad))
    try:
        datos = await clima_servicio.clima(ciudad)
    except clima_servicio.ClimaNoDisponible as e:
        raise HTTPException(502, str(e))
    ph, humedad = None, None
    try:
        ph, humedad = await asyncio.wait_for(asyncio.shield(asyncio.gather(tarea_ph, tarea_humedad)), ESPERA_SUELO_SEGUNDOS)
    except asyncio.TimeoutError:
        pass
    hoy = {**datos["hoy"], "phSuelo": ph}
    if humedad is not None:
        hoy["humedadSuelo"] = round(humedad)
    # `datos` está en la caché del clima: se copia en vez de modificarlo
    return {**datos, "hoy": hoy}


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
        datos = await clima_servicio.clima(ciudad)  # misma caché que /clima: no gasta otra consulta
    except clima_servicio.ClimaNoDisponible as e:
        raise HTTPException(502, str(e))
    dia = hoy or db.hoy()
    activos = plan_servicio.siembras_en_curso(con, plan_id, dia)
    try:  # sin esta lluvia solo faltan las alertas de sequía: el resto se calcula igual
        reciente = await nasa_power.periodo(ciudad.lat, ciudad.lon, dia - timedelta(days=30), dia)
    except nasa_power.ErrorNasaPower:
        reciente = None
    suelo = None
    if activos:  # solo se pide la humedad del suelo si hay cultivos a los que avisar
        try:
            suelo = await asyncio.wait_for(suelo_ubicacion.humedad_vs_normal(ciudad), ESPERA_SUELO_SEGUNDOS)
        except asyncio.TimeoutError:
            suelo = None
    fichas = catalogo_cultivos.fichas_de(activos)
    # Plagas por cultivo con el motor (EPPO): lo que ya esté calculado entra; lo demás se calcula en segundo plano
    # y mientras tanto avisan las reglas generales
    plagas = motor_plagas.para_alertas(fichas, ciudad)
    return alertas.calcular(datos, activos, dia, fichas, reciente, suelo, plagas)


@router.get("/cultivos-activos", response_model=list[CultivoActivoOut])
def cultivos_activos(
    plan_id: int | None = Query(default=None, alias="planId"),
    hoy: date | None = None,
    municipio: str | None = None,
    con=Depends(db.con_db),
):
    """Siembras en curso hoy en un plan (por defecto el primero), la que cosecha primero va primero.

    `hoy` (AAAA-MM-DD) lo manda el navegador para usar su fecha local; sin él se usa la de Monterrey.
    `municipio` (la ubicación activa) elige el estado de cuyos datos de SIAP sale el precio y el
    rendimiento de cada cultivo; sin él, o si no tiene estado, se usan los nacionales.
    """
    activos = plan_servicio.siembras_en_curso(con, plan_id, hoy or db.hoy())
    lugar = ubicaciones.buscar(con, municipio) if municipio else None
    cve_ent = lugar.cve_ent if lugar else None
    for a in activos:
        a["mercado"] = catalogo_cultivos.mercado(a["cultivo"].get("catalogo_id"), cve_ent)
    return activos


@router.get("/tareas-vencidas", response_model=TareasVencidasOut)
def tareas_vencidas(
    plan_id: int | None = Query(default=None, alias="planId"),
    hoy: date | None = None,
    con=Depends(db.con_db),
):
    """Tareas del Planificador sin hacer cuya fecha ya pasó (por defecto del primer plan).

    No depende del clima: Principal las muestra aunque falle el pronóstico.
    """
    return tareas.vencidas(con, plan_id, hoy or db.hoy())
