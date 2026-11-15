"""Elige de dónde sale el clima: Meteomatics si hay llaves y responde; si no, Open-Meteo.

Principal, las alertas y Noticias piden el clima aquí y no les importa la fuente: el resultado trae
`fuente` ("Meteomatics" u "Open-Meteo") para que la pantalla lo muestre.
"""

from app import config
from app.services import meteomatics, openmeteo
from app.services.ubicaciones import Ubicacion


class ClimaNoDisponible(Exception):
    """Ninguna fuente de clima respondió."""


async def clima(m: Ubicacion) -> dict:
    motivo = None
    if config.METEOMATICS_USER and config.METEOMATICS_PASSWORD:
        try:
            return await meteomatics.clima(m)
        except meteomatics.MeteomaticsError as e:
            motivo = str(e)  # Meteomatics falló: se intenta el respaldo
    try:
        return await openmeteo.clima(m)
    except openmeteo.OpenMeteoError as e:
        detalle = f"{motivo}; {e}" if motivo else f"No Meteomatics keys are set and {e}"
        raise ClimaNoDisponible(detalle) from e
