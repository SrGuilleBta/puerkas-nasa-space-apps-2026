import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.services import clima as clima_servicio
from app.services import condiciones_locales, mapa_clima, openmeteo, suelo_ubicacion, ubicaciones

router = APIRouter(prefix="/api/clima", tags=["clima"])

ESPERA_SUELO_SEGUNDOS = 6


@router.get("/mapa")
async def mapa(con=Depends(db.con_db)):
    """Pronóstico de 7 días de lluvia (mm) y temperatura máxima (°C) sobre México, en una malla de puntos, más el
    contorno del país y los lugares guardados. Con caché de 3 horas; ver `services/mapa_clima.py`. La máxima de los
    lugares guardados es la del clima de Principal (`fuenteLugares` dice cuál)."""
    guardadas = ubicaciones.listar(con)
    try:
        datos = await mapa_clima.mapa([(u.nombre, u.lat, u.lon) for u in guardadas])
    except mapa_clima.ErrorMapaClima as e:
        raise HTTPException(502, str(e))
    # La máxima de cada lugar guardado se toma del mismo pronóstico que Principal (misma caché de 10 min), para que
    # coincidan; si alguno falla, ese lugar conserva el valor de Open-Meteo y el mapa sale igual.
    pronosticos = await asyncio.gather(*(clima_servicio.clima(u) for u in guardadas), return_exceptions=True)
    return mapa_clima.con_pronostico_de_principal(datos, list(pronosticos))


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
    # El clima de Principal (misma caché: las cifras coinciden) y los extras por hora de Open-Meteo; si falla uno
    # se muestra lo del otro.
    compartido, extras = await asyncio.gather(
        clima_servicio.clima(ciudad), condiciones_locales.condiciones(ciudad), return_exceptions=True
    )
    compartido = None if isinstance(compartido, clima_servicio.ClimaNoDisponible) else compartido
    extras = None if isinstance(extras, openmeteo.OpenMeteoError) else extras
    for resultado in (compartido, extras):
        if isinstance(resultado, BaseException):
            raise resultado  # un error que no se esperaba no se esconde
    datos = condiciones_locales.unir(compartido, extras)
    if datos is None:
        tarea_humedad.cancel()
        raise HTTPException(502, "Could not get the weather for this location")
    humedad = None
    try:
        humedad = await asyncio.wait_for(asyncio.shield(tarea_humedad), ESPERA_SUELO_SEGUNDOS)
    except asyncio.TimeoutError:
        pass  # sigue consultando de fondo y queda en caché para la próxima vez
    return {**datos, "humedadSuelo": None if humedad is None else round(humedad)}
