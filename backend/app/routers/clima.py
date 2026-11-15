import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.services import condiciones_locales, mapa_clima, openmeteo, suelo_ubicacion, ubicaciones

router = APIRouter(prefix="/api/clima", tags=["clima"])

ESPERA_SUELO_SEGUNDOS = 6


@router.get("/mapa")
async def mapa(con=Depends(db.con_db)):
    """Pronóstico de 7 días de lluvia (mm) y temperatura máxima (°C) sobre México, en una malla de puntos, más el
    contorno del país y los lugares guardados. Con caché de 3 horas; ver `services/mapa_clima.py`."""
    lugares = [(u.nombre, u.lat, u.lon) for u in ubicaciones.listar(con)]
    try:
        return await mapa_clima.mapa(lugares)
    except mapa_clima.ErrorMapaClima as e:
        raise HTTPException(502, str(e))


@router.get("/local")
async def local(municipio: str, con=Depends(db.con_db)):
    """Condiciones de hoy en una ubicación guardada: temperatura, viento (con dirección), lluvia esperada, humedad y
    temperatura del suelo, y la ventana para labores de campo. Ver `services/condiciones_locales.py`.

    La humedad del suelo viene del módulo Suelo (la misma cifra que Principal); si tarda más de 6 s queda en null y el
    resto se muestra igual.
    """
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
    tarea_humedad = asyncio.ensure_future(suelo_ubicacion.humedad_raiz(ciudad))
    try:
        datos = await condiciones_locales.condiciones(ciudad)
    except openmeteo.OpenMeteoError as e:
        tarea_humedad.cancel()
        raise HTTPException(502, str(e))
    humedad = None
    try:
        humedad = await asyncio.wait_for(asyncio.shield(tarea_humedad), ESPERA_SUELO_SEGUNDOS)
    except asyncio.TimeoutError:
        pass  # sigue consultando de fondo y queda en caché para la próxima vez
    # `datos` está en la caché: se copia en vez de modificarlo
    return {**datos, "humedadSuelo": None if humedad is None else round(humedad)}
