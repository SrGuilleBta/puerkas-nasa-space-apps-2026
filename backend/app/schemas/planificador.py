"""Modelos de entrada y salida de la API del Planificador.

Hacia afuera los nombres van en camelCase (fechaSiembra, cicloDias), igual que el resto de la
API que consume el frontend; por dentro se usa snake_case.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
HECTAREAS_MAX = 100_000


class Modelo(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------- Entrada ----------
class PlanIn(Modelo):
    nombre: Nombre


class ParcelaIn(Modelo):
    nombre: Nombre
    hectareas: float = Field(gt=0, le=HECTAREAS_MAX)


class ParcelaPatch(Modelo):
    nombre: Nombre | None = None
    hectareas: float | None = Field(default=None, gt=0, le=HECTAREAS_MAX)


class CultivoIn(Modelo):
    nombre: Nombre
    tipo: Nombre  # cereal, leguminosa, frutal...
    ciclo_dias: int = Field(gt=0, le=1500)


class SiembraIn(Modelo):
    cultivo_id: int
    fecha_siembra: date
    # Si no se manda, la cosecha se calcula con el ciclo del cultivo y las hectáreas son las de la parcela
    fecha_cosecha: date | None = None
    hectareas: float | None = Field(default=None, gt=0, le=HECTAREAS_MAX)


class SiembraPatch(Modelo):
    """Solo se cambia lo que se manda."""

    cultivo_id: int | None = None
    fecha_siembra: date | None = None
    fecha_cosecha: date | None = None
    hectareas: float | None = Field(default=None, gt=0, le=HECTAREAS_MAX)


# ---------- Salida ----------
class CultivoOut(Modelo):
    id: int
    nombre: str
    tipo: str
    ciclo_dias: int


class SiembraOut(Modelo):
    id: int
    parcela_id: int
    cultivo: CultivoOut
    fecha_siembra: date
    fecha_cosecha: date
    hectareas: float


class ParcelaOut(Modelo):
    id: int
    plan_id: int
    nombre: str
    hectareas: float
    siembras: list[SiembraOut] = []


class PlanResumenOut(Modelo):
    id: int
    nombre: str


class PlanOut(PlanResumenOut):
    parcelas: list[ParcelaOut] = []


class ParcelaResumenOut(Modelo):
    id: int
    nombre: str


class CultivoActivoOut(SiembraOut):
    """Una siembra en curso hoy, con lo que Principal necesita para mostrarla."""

    parcela: ParcelaResumenOut
    dia: int  # día del ciclo, desde 1
    dias_totales: int
    avance: int  # % del ciclo transcurrido
    etapa: int
    etapas: int


class ProximaCosechaOut(Modelo):
    fecha: date
    dias_restantes: int
    cultivo: str
    parcela: str


class ResumenOut(Modelo):
    total_siembras: int
    cultivos_distintos: int
    en_curso: int
    hectareas_totales: float
    hectareas_en_uso: float
    uso_suelo: int  # % de la superficie del plan que tiene un cultivo en curso hoy
    proxima_cosecha: ProximaCosechaOut | None = None


class DespuesDeOut(Modelo):
    cultivo: CultivoOut
    fecha_cosecha: date


class RecomendacionOut(Modelo):
    parcela: ParcelaResumenOut
    despues_de: DespuesDeOut
    sugerido: CultivoOut
    desde: date  # primer día en que se puede sembrar
    razon: str


class AnalisisOut(Modelo):
    resumen: ResumenOut
    recomendaciones: list[RecomendacionOut] = []
