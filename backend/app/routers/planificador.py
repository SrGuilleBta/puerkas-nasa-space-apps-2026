"""Rutas HTTP del Planificador. Sin lógica: valida la entrada y llama al servicio."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic.alias_generators import to_camel

from app import db
from app.schemas.planificador import (
    AnalisisOut,
    CatalogoIn,
    CatalogoItemOut,
    CultivoIn,
    CultivoOut,
    ParcelaIn,
    ParcelaOut,
    ParcelaPatch,
    PlanIn,
    PlanOut,
    PlanResumenOut,
    SiembraIn,
    SiembraOut,
    SiembraPatch,
)
from app.services import catalogo_cultivos, nasa_power, ubicaciones, ventana_siembra
from app.services import planificador as servicio

router = APIRouter(prefix="/api/planificador", tags=["planificador"])


con_db = db.con_db


# ---------- Errores ----------
ESTADO = {servicio.NoEncontrado: 404, servicio.Invalido: 422, servicio.Conflicto: 409}


def _a_camel(valor):
    if isinstance(valor, dict):
        return {to_camel(k): _a_camel(v) for k, v in valor.items()}
    return valor


async def error_planificador(_request: Request, error: servicio.ErrorPlanificador):
    """Todos los errores salen igual: {"detail": {"mensaje": "...", ...datos extra...}}."""
    cuerpo = {"mensaje": error.mensaje, **_a_camel(error.extra)}
    return JSONResponse(status_code=ESTADO[type(error)], content={"detail": cuerpo})


# ---------- Planes ----------
@router.get("/planes", response_model=list[PlanResumenOut])
def listar_planes(con=Depends(con_db)):
    return servicio.listar_planes(con)


@router.post("/planes", response_model=PlanResumenOut, status_code=201)
def crear_plan(datos: PlanIn, con=Depends(con_db)):
    return servicio.crear_plan(con, datos.nombre)


@router.get("/planes/{plan_id}", response_model=PlanOut)
def obtener_plan(plan_id: int, con=Depends(con_db)):
    """El plan completo: sus parcelas y, en cada una, sus siembras ordenadas por fecha."""
    return servicio.obtener_plan(con, plan_id)


@router.get("/planes/{plan_id}/analisis", response_model=AnalisisOut)
def analisis_plan(plan_id: int, hoy: date | None = None, con=Depends(con_db)):
    """Resumen del ciclo (siembras, uso del suelo, próxima cosecha) y qué sembrar después en cada parcela.

    `hoy` (AAAA-MM-DD) lo manda el navegador para usar su fecha local; sin él se usa la de Monterrey.
    """
    return servicio.analisis_plan(con, plan_id, hoy or db.hoy())


@router.patch("/planes/{plan_id}", response_model=PlanResumenOut)
def renombrar_plan(plan_id: int, datos: PlanIn, con=Depends(con_db)):
    return servicio.renombrar_plan(con, plan_id, datos.nombre)


@router.delete("/planes/{plan_id}", status_code=204)
def borrar_plan(plan_id: int, con=Depends(con_db)):
    servicio.borrar_plan(con, plan_id)
    return Response(status_code=204)


# ---------- Parcelas ----------
@router.post("/planes/{plan_id}/parcelas", response_model=ParcelaOut, status_code=201)
def crear_parcela(plan_id: int, datos: ParcelaIn, con=Depends(con_db)):
    return servicio.crear_parcela(con, plan_id, datos.nombre, datos.hectareas)


@router.patch("/parcelas/{parcela_id}", response_model=ParcelaOut)
def editar_parcela(parcela_id: int, datos: ParcelaPatch, con=Depends(con_db)):
    return servicio.editar_parcela(con, parcela_id, datos.nombre, datos.hectareas)


@router.delete("/parcelas/{parcela_id}", status_code=204)
def borrar_parcela(parcela_id: int, con=Depends(con_db)):
    servicio.borrar_parcela(con, parcela_id)
    return Response(status_code=204)


# ---------- Catálogo de cultivos ----------
@router.get("/cultivos", response_model=list[CultivoOut])
def listar_cultivos(q: str | None = None, con=Depends(con_db)):
    """Catálogo; con `q` filtra por nombre sin importar acentos ni mayúsculas."""
    return servicio.listar_cultivos(con, q)


@router.post("/cultivos", response_model=CultivoOut, status_code=201)
def crear_cultivo(datos: CultivoIn, con=Depends(con_db)):
    return servicio.crear_cultivo(con, datos.nombre, datos.tipo, datos.ciclo_dias)


@router.get("/catalogo", response_model=list[CatalogoItemOut])
def listar_catalogo():
    """Cultivos del catálogo de Cultivos (los que se pueden elegir al sembrar)."""
    return catalogo_cultivos.listar()


@router.post("/cultivos/desde-catalogo", response_model=CultivoOut, status_code=201)
def cultivo_desde_catalogo(datos: CatalogoIn, con=Depends(con_db)):
    """Crea (o reutiliza) en el Planificador el cultivo elegido del catálogo."""
    return catalogo_cultivos.asegurar_cultivo(con, datos.catalogo_id)


@router.get("/catalogo/{catalogo_id}/ventana-siembra")
async def ventana_de_siembra(catalogo_id: str, municipio: str, con=Depends(con_db)):
    """Mejor época para sembrar un cultivo del catálogo en una ubicación guardada (temperatura ideal
    del cultivo contra el clima promedio mensual de NASA POWER)."""
    ficha = catalogo_cultivos.ficha_del_catalogo(catalogo_id)
    ciudad = ubicaciones.buscar(con, municipio)
    if ciudad is None:
        raise servicio.NoEncontrado(f"Unknown location: {municipio}")
    try:
        clima = await nasa_power.climatologia(ciudad.lat, ciudad.lon)
    except nasa_power.ErrorNasaPower as e:
        raise HTTPException(502, str(e))
    return ventana_siembra.calcular(ficha, clima["temp"], clima["lluviaMm"])


@router.get("/cultivos/{cultivo_id}/ficha")
def ficha_cultivo(cultivo_id: int, con=Depends(con_db)):
    """Ficha del catálogo (cuidados, temperatura, agua, suelo); null si el cultivo no viene del catálogo."""
    return catalogo_cultivos.ficha(con, cultivo_id)


# ---------- Siembras ----------
@router.post("/parcelas/{parcela_id}/siembras", response_model=SiembraOut, status_code=201)
def crear_siembra(parcela_id: int, datos: SiembraIn, con=Depends(con_db)):
    return servicio.crear_siembra(
        con, parcela_id, datos.cultivo_id, datos.fecha_siembra, datos.fecha_cosecha, datos.hectareas
    )


@router.patch("/siembras/{siembra_id}", response_model=SiembraOut)
def editar_siembra(siembra_id: int, datos: SiembraPatch, con=Depends(con_db)):
    return servicio.editar_siembra(con, siembra_id, datos.model_dump(exclude_unset=True))


@router.delete("/siembras/{siembra_id}", status_code=204)
def borrar_siembra(siembra_id: int, con=Depends(con_db)):
    servicio.borrar_siembra(con, siembra_id)
    return Response(status_code=204)
