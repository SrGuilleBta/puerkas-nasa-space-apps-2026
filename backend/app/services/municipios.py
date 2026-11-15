from dataclasses import dataclass


@dataclass(frozen=True)
class Municipio:
    nombre: str  # igual que en el selector del frontend
    lat: float
    lon: float
    zona: str  # zona horaria IANA
    # Punto de campo agrícola cercano para consultar el suelo. SoilGrids no tiene dato en las
    # zonas urbanas (el centro de la ciudad devuelve null), y al agricultor le sirve el suelo
    # del campo, no el de la ciudad. Cada punto está verificado: SoilGrids sí responde ahí.
    lat_suelo: float
    lon_suelo: float


MUNICIPIOS = [
    Municipio("Monterrey, NL", 25.6866, -100.3161, "America/Monterrey", 25.80, -100.00),  # Pesquería
    Municipio("Saltillo, COAH", 25.4232, -101.0053, "America/Monterrey", 25.44, -100.85),  # Arteaga
    Municipio("Culiacán, SIN", 24.8091, -107.3940, "America/Mazatlan", 24.60, -107.55),  # valle
    Municipio("Mérida, YUC", 20.9674, -89.5926, "America/Merida", 21.00, -89.87),  # Hunucmá
]


def buscar(nombre: str) -> Municipio | None:
    return next((m for m in MUNICIPIOS if m.nombre == nombre), None)
