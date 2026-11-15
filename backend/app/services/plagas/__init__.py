"""Motor de plagas por cultivo: cruza las plagas que EPPO asocia al cultivo (por su código `eppocode` del catálogo)
con las que hay en México y evalúa si el clima de la ubicación las favorece (reglas en `evaluar.py`).

Es lento la primera vez (decenas de consultas a EPPO, GBIF e iNaturalist), así que el análisis corre en segundo
plano: `pedir` devuelve de inmediato lo que haya en caché, o `{"estado": "calculando"}` y arranca el cálculo.
El resultado se guarda 6 horas por cultivo (código EPPO) y lugar. Las alertas y Noticias usan `en_cache` y `pedir`
sin esperar: si todavía no hay resultado, usan las reglas generales de `alertas.py`.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from functools import lru_cache

import httpx

from app import config
from app.config import BASE_DIR
from app.services.plagas import clima, eppo, evaluar, presencia

ARCHIVO_MX = BASE_DIR / "data" / "plagas" / "plagas_mx.json"
LIMITE_PLAGAS = 12  # plagas que se analizan por cultivo (las más extendidas en el país primero)
CONCURRENCIA = 4  # plagas que se evalúan al mismo tiempo
SEGUNDOS_RESULTADO = 6 * 3600
SEGUNDOS_ERROR = 300  # tras un fallo se espera antes de reintentar

# (código EPPO, lat, lon) -> (cuándo, resultado) / (cuándo, mensaje de error)
_resultados: dict[tuple, tuple[float, dict]] = {}
_errores: dict[tuple, tuple[float, str]] = {}
_tareas: dict[tuple, asyncio.Task] = {}


class PlagasNoDisponibles(Exception):
    """No se puede analizar este cultivo (sin llave de EPPO, sin código EPPO, sin clima...). El mensaje va a la pantalla."""


@lru_cache(maxsize=1)
def plagas_mx() -> dict[str, dict]:
    """Plagas presentes en México (catálogo de EPPO bajado a `data/plagas/plagas_mx.json`)."""
    try:
        with open(ARCHIVO_MX, encoding="utf-8") as f:
            return evaluar.plagas_presentes(json.load(f))
    except (OSError, ValueError) as e:
        raise PlagasNoDisponibles("The list of pests present in Mexico is missing (data/plagas/plagas_mx.json)") from e


def _llave(eppocode: str, lugar) -> tuple:
    return (eppocode.upper(), round(lugar.lat, 2), round(lugar.lon, 2))


def en_cache(eppocode: str | None, lugar) -> dict | None:
    """Resultado guardado y vigente, o None."""
    if not eppocode:
        return None
    guardado = _resultados.get(_llave(eppocode, lugar))
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_RESULTADO:
        return guardado[1]
    return None


async def _evaluar_plaga(cliente, codigo: str, pais: dict, serie: list[dict], lugar, cupo: asyncio.Semaphore) -> dict | None:
    async with cupo:
        crudo = await eppo.expediente_crudo(cliente, codigo)
        datos = evaluar.expediente(codigo, crudo, pais)
        if datos["tipo"] not in evaluar.TIPOS:
            return None  # maleza: el clima no dice nada de ella
        cerca = await presencia.cerca(cliente, datos["nombreCientifico"], lugar.lat, lugar.lon)
    meteo = evaluar.evaluar_clima(datos["tipo"], serie)
    final = evaluar.riesgo(meteo, cerca)
    return {
        **datos,
        "riesgo": final["nivel"],
        "diagnostico": final["diagnostico"],
        "accion": final["accion"],
        "rachaDias": meteo["rachaDias"],
        "gradosDia": meteo["gradosDia"],
        "diasFavorables": meteo["diasFavorables"],
        "presencia": cerca,
    }


async def analizar(eppocode: str, lugar) -> dict:
    """Análisis completo de un cultivo en un lugar. Lanza PlagasNoDisponibles o eppo.ErrorEppo."""
    pais = plagas_mx()
    try:
        async with httpx.AsyncClient(timeout=20) as cliente:
            serie, de_cultivo = await asyncio.gather(
                clima.serie(cliente, lugar.lat, lugar.lon, lugar.zona),
                eppo.plagas_de_cultivo(cliente, eppocode),
            )
            clase = {}
            for p in de_cultivo:
                codigo = str(p.get("eppocode") or "").strip().upper()
                prioridad = evaluar.clase_de(p)
                if codigo and codigo in pais and prioridad is not None:
                    clase[codigo] = min(prioridad, clase.get(codigo, prioridad))
            # Primero las plagas con este cultivo como hospedero principal, y dentro de cada grupo las más extendidas
            candidatas = sorted(clase, key=lambda c: (clase[c], evaluar.PRIORIDAD_ESTADO.get(pais[c]["estado"], 99), c))

            cupo = asyncio.Semaphore(CONCURRENCIA)
            tareas = [_evaluar_plaga(cliente, c, pais[c], serie, lugar, cupo) for c in candidatas[: int(LIMITE_PLAGAS * 1.5)]]
            salidas = await asyncio.gather(*tareas, return_exceptions=True)
    except clima.ErrorClima as e:
        raise PlagasNoDisponibles(str(e)) from e
    except eppo.SinLlave as e:
        raise PlagasNoDisponibles(str(e)) from e

    errores = [s for s in salidas if isinstance(s, eppo.ErrorEppo)]
    if errores and len(errores) == len(salidas):
        raise errores[0]  # EPPO no respondió en ninguna: no se guarda un "todo bien" falso
    plagas = [s for s in salidas if isinstance(s, dict)][:LIMITE_PLAGAS]
    plagas.sort(key=lambda p: (evaluar.ORDEN[p["riesgo"]], p["eppocode"]))

    return {
        "eppocode": eppocode.upper(),
        "ubicacion": lugar.nombre,
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "ventana": {"desde": serie[0]["fecha"], "hasta": serie[-1]["fecha"]},
        "totalEnPais": len(candidatas),
        "analizadas": len(plagas),
        "incompleto": bool(errores),  # alguna plaga no se pudo consultar
        **evaluar.resumen(plagas),
        "plagas": plagas,
    }


async def _calcular(llave: tuple, eppocode: str, lugar) -> None:
    try:
        _resultados[llave] = (time.monotonic(), await analizar(eppocode, lugar))
        _errores.pop(llave, None)
    except (PlagasNoDisponibles, eppo.ErrorEppo) as e:
        _errores[llave] = (time.monotonic(), str(e))
    except Exception as e:  # noqa: BLE001 - una tarea en segundo plano no puede dejar la app con un error sin avisar
        _errores[llave] = (time.monotonic(), f"Unexpected error ({type(e).__name__})")
    finally:
        _tareas.pop(llave, None)


def pedir(eppocode: str | None, lugar) -> dict:
    """Estado del análisis de un cultivo en un lugar, sin esperar. Hay que llamarla dentro de una tarea asyncio.

    - {"estado": "listo", ...resultado}: hay un análisis vigente.
    - {"estado": "calculando"}: se está calculando (se arranca si hacía falta); volver a pedir en unos segundos.
    - {"estado": "error" | "no_disponible", "mensaje": ...}: no se pudo; "error" se reintenta tras unos minutos.
    """
    if not eppocode:
        return {"estado": "no_disponible", "mensaje": "This crop has no EPPO code, so its pests cannot be looked up yet."}
    if not config.EPPO_API_KEY:
        return {"estado": "no_disponible", "mensaje": "The pest engine needs EPPO_API_KEY in .env."}
    llave = _llave(eppocode, lugar)

    listo = en_cache(eppocode, lugar)
    if listo is not None:
        return {"estado": "listo", **listo}
    if llave in _tareas:
        return {"estado": "calculando"}
    fallo = _errores.get(llave)
    if fallo and time.monotonic() - fallo[0] < SEGUNDOS_ERROR:
        return {"estado": "error", "mensaje": fallo[1]}
    _tareas[llave] = asyncio.get_running_loop().create_task(_calcular(llave, eppocode, lugar))
    return {"estado": "calculando"}


def para_alertas(fichas: dict[str, dict], lugar) -> dict[str, dict]:
    """Resultados vigentes de los cultivos con ficha (por id del catálogo). Los que faltan se piden en segundo plano.

    Sin llave de EPPO no hace nada. Hay que llamarla dentro de una tarea asyncio.
    """
    if not config.EPPO_API_KEY:
        return {}
    resultados = {}
    for catalogo_id, ficha in fichas.items():
        codigo = ficha.get("eppocode")
        if not codigo:
            continue
        respuesta = pedir(codigo, lugar)
        if respuesta["estado"] == "listo":
            resultados[catalogo_id] = respuesta
    return resultados
