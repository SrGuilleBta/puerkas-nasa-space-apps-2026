import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app import db
from app.services import alertas, catalogo_cultivos, meteomatics, nasa_power, noticias, ubicaciones
from app.services import planificador as plan_servicio

router = APIRouter(prefix="/api/noticias", tags=["noticias"])


@router.get("")
async def listar(
    municipio: str,
    plan_id: int | None = Query(default=None, alias="planId"),
    hoy: date | None = None,
    con=Depends(db.con_db),
):
    """Noticias propias (alertas, cosechas cercanas, lluvia reciente) seguidas de titulares externos.

    Cada fuente falla por separado: si no responde Meteomatics, NASA POWER o un feed, esa parte se
    omite y `externasCompletas` indica si todos los feeds respondieron.
    """
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise HTTPException(404, f"Unknown location: {municipio}")
    dia = hoy or db.hoy()

    clima, nasa, ext = await asyncio.gather(
        meteomatics.clima(ciudad),
        nasa_power.periodo(ciudad.lat, ciudad.lon, dia - timedelta(days=30), dia),
        noticias.externas(),
        return_exceptions=True,
    )
    activos = plan_servicio.siembras_en_curso(con, plan_id, dia)
    lista_alertas = alertas.calcular(clima, activos, dia, catalogo_cultivos.fichas_de(activos), nasa if isinstance(nasa, dict) else None) if isinstance(clima, dict) else []
    propias = noticias.propias(lista_alertas, activos, nasa if isinstance(nasa, dict) else None, ciudad.nombre, dia)
    externas, completas = ext if isinstance(ext, tuple) else ([], False)
    return {"items": propias + externas, "externasCompletas": completas}
