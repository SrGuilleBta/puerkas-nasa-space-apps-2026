"""Modelos de la API de ubicaciones."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class MiUbicacionIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    zona: Texto  # zona horaria IANA, p. ej. "America/Monterrey"


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UbicacionIn(MiUbicacionIn):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    nombre: Texto
    cve_ent: str | None = None  # estado (clave INEGI); lo trae el buscador de lugares


class EstadoPatch(_Camel):
    cve_ent: str | None = None  # null borra el estado


class UbicacionOut(_Camel):
    id: int
    nombre: str
    lat: float
    lon: float
    zona: str
    cve_ent: str | None = None


class CandidatoOut(_Camel):
    nombre: str
    lat: float
    lon: float
    zona: str
    cve_ent: str | None = None


class EstadoOut(BaseModel):
    clave: str
    nombre: str
