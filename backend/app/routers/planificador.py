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
    DuplicarPlanIn,
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
    TareaIn,
    TareaOut,
    TareaPatch,
)
from app.services import catalogo_cultivos, nasa_power, plan_extras, rotacion, tareas, ubicaciones, ventana_siembra
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


@router.post("/planes/{plan_id}/duplicar", response_model=PlanResumenOut, status_code=201)
def duplicar_plan(plan_id: int, datos: DuplicarPlanIn, con=Depends(con_db)):
    """Copia el plan (parcelas y siembras) moviendo las fechas `anios` años: el plan del año siguiente."""
    return plan_extras.duplicar_plan(con, plan_id, datos.nombre, datos.anios)


@router.get("/planes/{plan_id}/exportar")
def exportar_plan(plan_id: int, con=Depends(con_db)):
    """El plan en CSV (parcela, cultivo, fechas, hectáreas y economía), para Excel o Google Sheets."""
    archivo, contenido = plan_extras.exportar_csv(con, plan_id)
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )


@router.get("/planes/{plan_id}/exportar-pdf")
def exportar_plan_pdf(plan_id: int, hoy: date | None = None, con=Depends(con_db)):
    """El plan en PDF (resumen, calendario por parcela y tabla de siembras con su economía).

    `hoy` (AAAA-MM-DD) lo manda el navegador para usar su fecha local; sin él se usa la de Monterrey.
    """
    try:
        # Se importa aquí y no arriba: si falta la librería (hay que recrear el contenedor después de agregarla
        # a requirements.txt), solo falla el PDF y el resto de la app sigue funcionando.
        from app.services import plan_pdf
    except ImportError:
        raise HTTPException(
            503, "PDF export needs the fpdf2 library. Recreate the backend: docker compose up -d --force-recreate backend"
        )
    archivo, contenido = plan_pdf.exportar_pdf(con, plan_id, hoy or db.hoy())
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )


@router.get("/planes/{plan_id}", response_model=PlanOut)
def obtener_plan(plan_id: int, con=Depends(con_db)):
    """El plan completo: sus parcelas y, en cada una, sus siembras ordenadas por fecha."""
    return servicio.obtener_plan(con, plan_id)


@router.get("/planes/{plan_id}/analisis", response_model=AnalisisOut)
def analisis_plan(plan_id: int, hoy: date | None = None, con=Depends(con_db)):
    """Resumen del ciclo (siembras, uso del suelo, próxima cosecha) y qué sembrar después en cada parcela.

    `hoy` (AAAA-MM-DD) lo manda el navegador para usar su fecha local; sin él se usa la de Monterrey.
    """
    return rotacion.analisis(con, plan_id, hoy or db.hoy())


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


def _estado_de(con, municipio: str | None) -> str | None:
    """Estado (clave INEGI) de la ubicación activa, si se conoce."""
    ciudad = ubicaciones.buscar(con, municipio) if municipio else None
    return ciudad.cve_ent if ciudad else None


@router.get("/cultivos/{cultivo_id}/ficha")
def ficha_cultivo(cultivo_id: int, municipio: str | None = None, con=Depends(con_db)):
    """Ficha del catálogo (cuidados, temperatura, agua, suelo, manejo del INIFAP del estado de la ubicación y
    cifras sugeridas de costos); null si el cultivo no viene del catálogo."""
    return catalogo_cultivos.ficha(con, cultivo_id, _estado_de(con, municipio))


@router.get("/catalogo/{catalogo_id}/ficha")
def ficha_del_catalogo(catalogo_id: str, municipio: str | None = None, con=Depends(con_db)):
    """Lo mismo, para un cultivo del catálogo que todavía no está en el Planificador."""
    ficha = catalogo_cultivos.ficha_por_catalogo(catalogo_id, _estado_de(con, municipio))
    if ficha is None:
        raise servicio.NoEncontrado(f"The catalog has no crop \"{catalogo_id}\"")
    return ficha


# ---------- Siembras ----------
@router.post("/parcelas/{parcela_id}/siembras", response_model=SiembraOut, status_code=201)
def crear_siembra(parcela_id: int, datos: SiembraIn, con=Depends(con_db)):
    return servicio.crear_siembra(
        con, parcela_id, datos.cultivo_id, datos.fecha_siembra, datos.fecha_cosecha, datos.hectareas,
        datos.model_dump(include={"rendimiento_t_ha", "precio_t", "costo_ha"}),
    )


@router.patch("/siembras/{siembra_id}", response_model=SiembraOut)
def editar_siembra(siembra_id: int, datos: SiembraPatch, con=Depends(con_db)):
    return servicio.editar_siembra(con, siembra_id, datos.model_dump(exclude_unset=True))


@router.delete("/siembras/{siembra_id}", status_code=204)
def borrar_siembra(siembra_id: int, con=Depends(con_db)):
    servicio.borrar_siembra(con, siembra_id)
    return Response(status_code=204)


# ---------- Tareas de una siembra ----------
@router.get("/siembras/{siembra_id}/tareas", response_model=list[TareaOut])
def listar_tareas(siembra_id: int, con=Depends(con_db)):
    return tareas.listar(con, siembra_id)


@router.post("/siembras/{siembra_id}/tareas", response_model=TareaOut, status_code=201)
def crear_tarea(siembra_id: int, datos: TareaIn, con=Depends(con_db)):
    return tareas.crear(con, siembra_id, datos.titulo, datos.tipo, datos.fecha)


@router.post("/siembras/{siembra_id}/tareas/sugeridas", response_model=list[TareaOut], status_code=201)
def tareas_sugeridas(siembra_id: int, con=Depends(con_db)):
    """Calendario general repartido a lo largo del ciclo; solo si la siembra aún no tiene tareas."""
    return tareas.sugeridas(con, siembra_id)


@router.patch("/tareas/{tarea_id}", response_model=TareaOut)
def editar_tarea(tarea_id: int, datos: TareaPatch, con=Depends(con_db)):
    return tareas.editar(con, tarea_id, datos.model_dump(exclude_unset=True))


@router.delete("/tareas/{tarea_id}", status_code=204)
def borrar_tarea(tarea_id: int, con=Depends(con_db)):
    tareas.borrar(con, tarea_id)
    return Response(status_code=204)
