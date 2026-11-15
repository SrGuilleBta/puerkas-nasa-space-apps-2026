"""Cliente de la API v2 de EPPO (https://api.eppo.int/gd/v2): plagas de un cultivo y expediente de cada plaga.

La llave sale de EPPO_API_KEY. Las respuestas se guardan en disco (ver cache.py): las plagas de un
cultivo 30 días y el expediente de una plaga 60.
"""

import asyncio
import weakref

import httpx

from app import config
from app.services.plagas import cache

BASE = "https://api.eppo.int/gd/v2"
DIAS_PLAGAS_DE_CULTIVO = 30
DIAS_EXPEDIENTE = 60
REINTENTOS = 2
CONCURRENCIA = 6  # consultas a EPPO al mismo tiempo: más provoca respuestas 429

_cupos: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


def _cupo() -> asyncio.Semaphore:
    """Un semáforo por bucle de eventos (uno solo no sirve si la app se arranca más de una vez, como en las pruebas)."""
    bucle = asyncio.get_running_loop()
    if bucle not in _cupos:
        _cupos[bucle] = asyncio.Semaphore(CONCURRENCIA)
    return _cupos[bucle]

# Endpoints de un taxón que forman el expediente de una plaga
ENDPOINTS_EXPEDIENTE = ("kingdom", "taxonomy", "names", "hosts", "vectors", "bcas", "categorization", "photos")


class ErrorEppo(Exception):
    """EPPO no respondió o rechazó la llave."""


class SinLlave(ErrorEppo):
    """Falta EPPO_API_KEY."""


async def pedir(cliente: httpx.AsyncClient, ruta: str):
    """GET a EPPO; None si no existe (404). Reintenta ante 429 y errores del servidor."""
    if not config.EPPO_API_KEY:
        raise SinLlave("EPPO_API_KEY is missing from .env")
    url = f"{BASE}/{ruta.lstrip('/')}"
    for intento in range(REINTENTOS + 1):
        try:
            async with _cupo():
                r = await cliente.get(url, headers={"X-Api-Key": config.EPPO_API_KEY, "Accept": "application/json"})
        except httpx.HTTPError as e:
            if intento == REINTENTOS:
                raise ErrorEppo(f"Could not connect to EPPO ({type(e).__name__})") from e
        else:
            if r.status_code == 404:
                return None
            if r.status_code in (401, 403):
                raise ErrorEppo("EPPO rejected the API key")
            if r.status_code < 400:
                try:
                    return r.json()
                except ValueError as e:
                    raise ErrorEppo("EPPO sent an unreadable answer") from e
            if r.status_code not in (429, 500, 502, 503, 504) or intento == REINTENTOS:
                raise ErrorEppo(f"EPPO responded with {r.status_code}")
        await asyncio.sleep(0.6 * (intento + 1))


def diccionarios(datos) -> list[dict]:
    """Los objetos de una respuesta de EPPO, sin importar cuánto estén anidados."""
    resultado = []
    if isinstance(datos, list):
        for item in datos:
            if isinstance(item, dict):
                resultado.append(item)
            elif isinstance(item, list):
                resultado.extend(diccionarios(item))
    elif isinstance(datos, dict):
        if any(k in datos for k in ("eppocode", "code", "fullname", "isolang", "url", "country", "isocode")):
            resultado.append(datos)
        for valor in datos.values():
            if isinstance(valor, (list, dict)):
                resultado.extend(diccionarios(valor))
    return resultado


async def plagas_de_cultivo(cliente: httpx.AsyncClient, cultivo: str) -> list[dict]:
    """Plagas que EPPO asocia a un cultivo (código EPPO), con caché de 30 días."""
    guardado = cache.leer("cultivo", cultivo, DIAS_PLAGAS_DE_CULTIVO)
    if guardado is not None:
        return guardado
    lista = diccionarios(await pedir(cliente, f"taxons/taxon/{cultivo}/pests"))
    cache.escribir("cultivo", cultivo, lista)
    return lista


async def expediente_crudo(cliente: httpx.AsyncClient, plaga: str) -> dict:
    """Respuestas de los 8 endpoints de EPPO de una plaga, con caché de 60 días.

    Si un endpoint falla (distinto de 404) no se guarda nada: se reintenta en la próxima consulta.
    """
    guardado = cache.leer("expediente", plaga, DIAS_EXPEDIENTE)
    if guardado is not None:
        return guardado

    async def uno(nombre: str):
        try:
            return nombre, await pedir(cliente, f"taxons/taxon/{plaga}/{nombre}"), True
        except ErrorEppo:
            return nombre, None, False

    respuestas = await asyncio.gather(*(uno(n) for n in ENDPOINTS_EXPEDIENTE))
    crudo = {nombre: datos for nombre, datos, _ in respuestas}
    if all(ok for _, _, ok in respuestas):
        cache.escribir("expediente", plaga, crudo)
    return crudo
