import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.services import alertas, catalogo_cultivos, mercado, nasa_power, noticias, tareas, ubicaciones
from app.services import clima as clima_servicio
from app.services import planificador as plan_servicio
from app.services import plagas as motor_plagas

router = APIRouter(prefix="/api/noticias", tags=["noticias"])


def _precios_de_mercado(activos: list[dict], ciudad, dia: date) -> list[dict]:
    """Tendencia del precio al consumidor (Profeco) de los cultivos en curso, una por producto; vacío si no hay datos."""
    try:
        estado = mercado.clave_de_estado(ciudad.cve_ent)
    except mercado.SinDatos:
        return []
    vistos, lista = set(), []
    for a in activos:
        t = mercado.tendencia(a["cultivo"].get("catalogo_id"), estado, dia)
        if t and t["producto"] not in vistos:
            vistos.add(t["producto"])
            lista.append(t)
    return lista


@router.get("")
async def listar(
    municipio: str,
    plan_id: int | None = Query(default=None, alias="planId"),
    hoy: date | None = None,
    con=Depends(db.con_db),
):
    """Noticias propias (alertas, tareas vencidas, cosechas cercanas, lluvia reciente) seguidas de titulares externos.

    Cada fuente falla por separado: si no responde Meteomatics, NASA POWER o un feed, esa parte se
    omite y `externasCompletas` indica si todos los feeds respondieron.
    """
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
    dia = hoy or db.hoy()

    clima, nasa, ext = await asyncio.gather(
        clima_servicio.clima(ciudad),
        nasa_power.periodo(ciudad.lat, ciudad.lon, dia - timedelta(days=30), dia),
        noticias.externas(),
        return_exceptions=True,
    )
    activos = plan_servicio.siembras_en_curso(con, plan_id, dia)
    fichas = catalogo_cultivos.fichas_de(activos)
    plagas = motor_plagas.para_alertas(fichas, ciudad)  # lo ya calculado; lo demás arranca en segundo plano
    lista_alertas = alertas.calcular(clima, activos, dia, fichas, nasa if isinstance(nasa, dict) else None, None, plagas) if isinstance(clima, dict) else []
    vencidas = tareas.vencidas(con, plan_id, dia)
    precios = _precios_de_mercado(activos, ciudad, dia)
    propias = noticias.propias(lista_alertas, activos, nasa if isinstance(nasa, dict) else None, ciudad.nombre, dia, vencidas, precios)
    externas, completas = ext if isinstance(ext, tuple) else ([], False)
    return {"items": propias + externas, "externasCompletas": completas}
