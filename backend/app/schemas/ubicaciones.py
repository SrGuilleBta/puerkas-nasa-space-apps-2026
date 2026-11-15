"""Modelos de la API de ubicaciones."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class MiUbicacionIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    zona: Texto  # zona horaria IANA, p. ej. "America/Monterrey"


class UbicacionIn(MiUbicacionIn):
    nombre: Texto


class UbicacionOut(BaseModel):
    id: int
    nombre: str
    lat: float
    lon: float
    zona: str


class CandidatoOut(BaseModel):
    nombre: str
    lat: float
    lon: float
    zona: str
