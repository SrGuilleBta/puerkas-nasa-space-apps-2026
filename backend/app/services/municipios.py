from dataclasses import dataclass


@dataclass(frozen=True)
class Municipio:
    nombre: str  # igual que en el selector del frontend
    lat: float
    lon: float
    zona: str  # zona horaria IANA


MUNICIPIOS = [
    Municipio("Monterrey, NL", 25.6866, -100.3161, "America/Monterrey"),
    Municipio("Saltillo, COAH", 25.4232, -101.0053, "America/Monterrey"),
    Municipio("Culiacán, SIN", 24.8091, -107.3940, "America/Mazatlan"),
    Municipio("Mérida, YUC", 20.9674, -89.5926, "America/Merida"),
]


def buscar(nombre: str) -> Municipio | None:
    return next((m for m in MUNICIPIOS if m.nombre == nombre), None)
