import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.services import ubicaciones
from app.services.suelo import grace, mapa, modis, smap, soilgrids, srtm
from app.services.suelo import nasa_power as suelo_power

router = APIRouter(prefix="/api/suelo", tags=["suelo"])


async def punto_de_ubicacion(nombre: str) -> tuple[float, float]:
    """Punto de suelo de una ubicación guardada (tabla `ubicacion`, ver db.py): SIEMPRE el píxel de
    cultivo más cercano al lugar según NASA MODIS (MCD12Q1), con la misma regla para todas las
    ubicaciones. No se usa `lat_suelo` de la tabla: al revisarlos con MODIS, 3 de los 4 puntos de inicio
    caían en pastizal o matorral, no en cultivo (y lo usa la Principal para el pH, que es otra cosa).
    Si no hay cultivo a ~50 km, o MODIS no responde, se usa el lugar mismo."""
    con = db.conectar()
    try:
        u = ubicaciones.buscar(con, nombre)
    finally:
        con.close()
    if u is None:
        raise HTTPException(404, f"Unknown location: {nombre}")
    try:
        c = await modis.cultivo_cercano(u.lat, u.lon)
    except Exception:  # noqa: BLE001 - sin MODIS se usa el lugar mismo
        c = None
    return (c["lat"], c["lon"]) if c else (u.lat, u.lon)


async def punto(
    municipio: str | None = Query(None, description='Ubicación guardada, ej. "Monterrey, NL"'),
    lat: float | None = Query(None, ge=-90, le=90, description="Latitud (si no se manda municipio)"),
    lon: float | None = Query(None, ge=-180, le=180, description="Longitud (si no se manda municipio)"),
) -> tuple[float, float]:
    """Punto a consultar: el de la ubicación guardada (`municipio`) o lat y lon directos."""
    if municipio:
        return await punto_de_ubicacion(municipio)
    if lat is None or lon is None:
        raise HTTPException(400, "Send municipio, or lat and lon")
    return lat, lon


PUNTO = Depends(punto)


@router.get("/actual")
async def actual(p: tuple[float, float] = PUNTO):
    """Humedad (superficie, raíz, perfil, en %) y temperatura del suelo del último día con datos."""
    lat, lon = p
    dato = await suelo_power.actual(lat, lon)
    if dato is None:
        raise HTTPException(404, "NASA POWER has no recent data for this point")
    return {**dato, "fuente": "NASA POWER"}


@router.get("/historico")
async def historico(
    p: tuple[float, float] = PUNTO,
    anio_inicio: int = Query(2005, ge=1981),
    anio_fin: int = Query(date.today().year - 1, ge=1981),
):
    """Serie mensual de humedad, temperatura del suelo y evaporación (mm/día), para la gráfica de tendencia."""
    lat, lon = p
    if anio_inicio > anio_fin:
        raise HTTPException(400, "anio_inicio must be less than or equal to anio_fin")
    serie = await suelo_power.mensual(lat, lon, anio_inicio, anio_fin)
    return {"serie": serie, "fuente": "NASA POWER (mensual)"}


@router.get("/estado")
async def estado(p: tuple[float, float] = PUNTO):
    """Qué tan seco o húmedo está el suelo comparado con otros años en esta época (SMAP): humedad
    medida de los últimos 30 días contra el mismo periodo de cada año desde 2015. Usa los cortes por
    percentil del Drought Monitor (D0-D4) como referencia, pero NO es una declaración de sequía."""
    lat, lon = p
    try:
        return await smap.estado_sequia(lat, lon)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.get("/propiedades")
async def propiedades(p: tuple[float, float] = PUNTO, municipio: str | None = Query(None)):
    """pH, textura (arcilla/arena/limo), carbono y materia orgánica en las capas 0-5 y 5-15 cm."""
    lat, lon = p
    try:
        return await soilgrids.propiedades(lat, lon, municipio)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


# Clases de pendiente de la FAO, Guidelines for Soil Description (4a ed., 2006), cuadro 5.
CLASES_PENDIENTE_FAO = [
    (0.2, "flat"),
    (0.5, "level"),
    (1, "nearly level"),
    (2, "very gently sloping"),
    (5, "gently sloping"),
    (10, "sloping"),
    (15, "strongly sloping"),
    (30, "moderately steep"),
    (60, "steep"),
]


def clase_pendiente(pct: float | None) -> str | None:
    if pct is None:
        return None
    for limite, nombre in CLASES_PENDIENTE_FAO:
        if pct <= limite:
            return nombre
    return "very steep"


@router.get("/erosion")
async def erosion(p: tuple[float, float] = PUNTO):
    """Datos para evaluar erosión: pendiente (NASA SRTM, 30 m) con su clase FAO y lluvias fuertes (NASA POWER)."""
    lat, lon = p
    try:
        terreno = await srtm.terreno(lat, lon)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    lluvias = await suelo_power.lluvias_fuertes(lat, lon)
    ls = await srtm.factor_ls(lat, lon)
    return {
        "clase_pendiente_fao": clase_pendiente(terreno["pendiente_promedio_pct"]),
        "terreno": terreno,
        "factor_ls": ls,
        "lluvias_fuertes": lluvias,
        "metodo": "Clases de pendiente FAO, Guidelines for Soil Description (2006); factor LS de la RUSLE",
        "fuente": "NASA SRTM (SRTMGL1) + NASA POWER (PRECTOTCORR)",
    }


@router.get("/agua-subterranea")
async def agua_subterranea(p: tuple[float, float] = PUNTO):
    """Tendencia del agua almacenada en la región (GRACE/GRACE-FO). La primera vez descarga ~46 MB."""
    lat, lon = p
    try:
        return await grace.agua_subterranea(lat, lon)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.get("/smap")
async def humedad_smap(p: tuple[float, float] = PUNTO):
    """Humedad superficial MEDIDA por satélite (NASA SMAP, 9 km) de los últimos 10 días."""
    lat, lon = p
    try:
        return await smap.humedad(lat, lon)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.get("/raiz")
async def humedad_raiz(p: tuple[float, float] = PUNTO):
    """Humedad de la zona de raíces (0-100 cm) con SMAP L4 (modelo de NASA corregido con SMAP)."""
    lat, lon = p
    try:
        return await smap.raiz(lat, lon)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.get("/retencion")
async def retencion(p: tuple[float, float] = PUNTO, dias: int = Query(45, ge=10, le=120)):
    """Humedad medida por SMAP y lluvia diaria de las últimas semanas: muestra cuánto sube la humedad
    con cada lluvia y qué tan rápido se va (cómo retiene el agua el suelo)."""
    lat, lon = p
    hoy = date.today()
    inicio = hoy - timedelta(days=dias)
    try:
        humedad = await smap.serie(lat, lon, [(inicio, hoy)])
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    lluvia = await suelo_power.lluvia_diaria(lat, lon, inicio, hoy)
    dias_lista = []
    for k in range(dias + 1):
        f = (inicio + timedelta(days=k)).isoformat()
        m = humedad.get(f)
        dias_lista.append({
            "fecha": f,
            "humedad_pct_volumen": m["humedad_pct_volumen"] if m else None,
            "lluvia_mm": lluvia.get(f),
        })
    return {
        "dias": dias_lista,
        "nota": "Rain for the last 2-3 days may be missing (NASA POWER has a delay). SMAP does not measure every day.",
        "fuente": "Humedad: NASA SMAP L3 (9 km) · Lluvia: NASA POWER (PRECTOTCORR)",
    }


@router.get("/cobertura")
async def cobertura(p: tuple[float, float] = PUNTO):
    """Cobertura vegetal y meses de suelo desnudo con NDVI de NASA MODIS (250 m)."""
    lat, lon = p
    try:
        return await modis.cobertura(lat, lon)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


ESPERA_RESUMEN_SEGUNDOS = 45


async def _con_limite(coro):
    """Corre una consulta con tiempo límite; si falla o tarda, devuelve el motivo en vez de romper."""
    try:
        return await asyncio.wait_for(coro, ESPERA_RESUMEN_SEGUNDOS), None
    except asyncio.TimeoutError:
        return None, "took too long (run scripts/precargar_suelo.py to cache it)"
    except Exception as e:  # noqa: BLE001 - se reporta en "faltantes"
        return None, str(e) or e.__class__.__name__


@router.get("/resumen")
async def resumen(p: tuple[float, float] = PUNTO, municipio: str | None = Query(None)):
    """TODO lo de suelo en una sola respuesta, ya clasificado con reglas oficiales, para que el
    PLANIFICADOR lo use al recomendar rotaciones. Ver docs/suelo.md, sección "Para el Planificador".

    Si una fuente no responde, su sección queda en null y el motivo aparece en `faltantes`.
    """
    lat, lon = p
    (humedad, e1), (agua, e2), (cob, e3), (ter, e4), (ls, e5), (lluvia, e6), (prop, e7), (hoy, e8) = await asyncio.gather(
        _con_limite(smap.estado_sequia(lat, lon)),
        _con_limite(grace.agua_subterranea(lat, lon)),
        _con_limite(modis.cobertura(lat, lon)),
        _con_limite(srtm.terreno(lat, lon)),
        _con_limite(srtm.factor_ls(lat, lon)),
        _con_limite(suelo_power.lluvias_fuertes(lat, lon)),
        _con_limite(soilgrids.propiedades(lat, lon, municipio)),
        _con_limite(suelo_power.actual(lat, lon)),
    )
    faltantes = {k: v for k, v in {
        "humedad_vs_normal": e1, "agua_subterranea": e2, "cobertura": e3, "terreno": e4 or e5 or e6,
        "propiedades": e7, "condiciones_hoy": e8,
    }.items() if v}

    capa = (prop or {}).get("capas", [{}])[0] if prop and not prop.get("sin_datos") else None
    return {
        "ubicacion": municipio,
        "punto": {"lat": lat, "lon": lon},
        # Humedad del suelo medida (SMAP) vs. el mismo periodo de otros años. NO es sequía oficial.
        "humedad_vs_normal": None if not humedad or humedad.get("mensaje") else {
            "clase": humedad["estado"],
            "codigo_referencia": humedad["categoria"],  # D0-D4 o null si no está más seco de lo normal
            "percentil": humedad["percentil"],
            "humedad_pct_volumen": humedad["humedad_promedio"],
            "promedio_historico_pct_volumen": humedad["promedio_historico_periodo"],
            "periodo": humedad["periodo"],
        },
        # Tendencia de largo plazo del agua almacenada en la región (GRACE): sostenibilidad del riego
        "agua_subterranea": None if not agua else {
            "tendencia_cm_por_anio": agua["tendencia_cm_por_anio"],
            "lectura": agua["lectura"],
        },
        # Cobertura vegetal (MODIS NDVI, clases USGS): en qué meses el terreno se queda sin plantas
        "cobertura": None if not cob else {
            "clase_actual": (cob.get("ultimo") or {}).get("clase"),
            "ndvi_actual": (cob.get("ultimo") or {}).get("ndvi"),
            "meses_suelo_desnudo": cob["meses_suelo_desnudo"],
            "mes_menor_cobertura": (cob.get("mes_menor_cobertura") or {}).get("mes"),
            "ndvi_por_mes": {m["mes"]: m["ndvi_promedio"] for m in cob["promedio_por_mes"]},
        },
        # Riesgo de erosión: forma del terreno (SRTM) y lluvias muy intensas (R20mm, OMM)
        "terreno": None if not ter else {
            "pendiente_pct": ter["pendiente_promedio_pct"],
            "clase_pendiente_fao": clase_pendiente(ter["pendiente_promedio_pct"]),
            "factor_ls_rusle": (ls or {}).get("ls_promedio"),
            "dias_lluvia_muy_intensa_por_anio": (lluvia or {}).get("dias_por_anio"),
        },
        # Suelo local (SoilGrids, capa 0-5 cm)
        "propiedades": None if not capa else {
            "textura_usda": capa["textura"],
            "ph": capa["ph"],
            "carbono_organico_g_kg": capa["carbono_organico_g_kg"],
            "materia_organica_estimada_pct": capa["materia_organica_estimada_pct"],
        },
        # Condiciones recientes del modelo NASA POWER
        "condiciones_hoy": None if not hoy else {
            "fecha": hoy["fecha"],
            "evaporacion_mm_dia": hoy["evaporacion_mm_dia"],
            "temperatura_superficie_c": hoy["temperatura_suelo"],
        },
        "faltantes": faltantes,
        "fuentes": "SMAP, GRACE/GRACE-FO, MODIS, SRTM y POWER (NASA); SoilGrids (ISRIC). Reglas: Drought Monitor, USGS, FAO, OMM, USDA.",
    }


@router.get("/mapa")
async def mapa_suelo(con=Depends(db.con_db)):
    """Humedad (raíz y superficie) y temperatura del suelo sobre todo México, con NASA POWER (malla de 0.5°), más los
    lugares guardados. Promedio de los últimos 7 días con dato; caché de 12 h. Ver services/suelo/mapa.py."""
    lugares = [(u.nombre, u.lat, u.lon) for u in ubicaciones.listar(con)]
    try:
        return await mapa.mapa(lugares)
    except mapa.ErrorMapaSuelo as e:
        raise HTTPException(503, str(e))
