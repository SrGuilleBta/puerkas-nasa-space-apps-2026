"""Proyección del suelo a 7 días: humedad de la zona de raíz, temperatura del suelo y pérdida de agua.

NO es una medición: es una estimación con un balance de agua diario muy simple, para ver hacia dónde va el suelo
(¿se seca o se moja esta semana?). Parte del último dato real de NASA POWER y avanza día por día con el pronóstico de
Open-Meteo.

Balance de agua (el planteamiento de la FAO, boletín 56, Allen et al. 1998: lo que entra con la lluvia menos lo que
sale por evapotranspiración):

    almacén(día) = almacén(día anterior) + lluvia − pérdida

- Almacén: la zona de raíz de POWER (`GWETROOT`) es 0-100 cm y se da como % de saturación. Se pasa a milímetros
  con `PROFUNDIDAD_MM` × `POROSIDAD` (supuestos: 1 000 mm de suelo y 45 % de poros, un suelo medio). Contra los datos
  de POWER (≈ 30 mm de lluvia suben la humedad ≈ 5 puntos) el orden de magnitud coincide.
- Lluvia: `precipitation_sum` de Open-Meteo. Los días entre el último dato de POWER (2-3 días de retraso) y hoy
  se llenan con la lluvia que Open-Meteo ya registró.
- Pérdida: la evapotranspiración de referencia del pronóstico (`et0_fao_evapotranspiration`, FAO Penman-Monteith)
  multiplicada por un factor que se **calibra con los últimos días de este mismo punto**: lo que POWER midió de
  evaporación (`EVLAND`) entre lo que Open-Meteo dio de ET0. Así la pérdida refleja cuánta agua pierde de verdad esta
  tierra, no un valor genérico.
- El almacén no baja de `MINIMO_PCT` ni sube de 100 % (no se modela el escurrimiento ni el drenaje).

Temperatura del suelo: la de la superficie (0 cm) del pronóstico de Open-Meteo, corregida con la diferencia promedio
que hubo los últimos días contra la de POWER (`TS`), para que la curva continúe sin saltos.

Límites: un solo punto de ~50 km (POWER), un suelo "medio" (no usa la textura de SoilGrids) y un pronóstico de lluvia
que se equivoca más mientras más lejos. Sirve para ver la tendencia, no para decidir un riego exacto. Por eso la
pantalla la dibuja punteada y la rotula como estimación.
"""

import time
from datetime import date, datetime, timedelta, timezone

from app.services import openmeteo
from app.services.openmeteo import OpenMeteoError
from app.services.suelo import nasa_power

PROFUNDIDAD_MM = 1000  # zona de raíz de POWER: 0-100 cm
POROSIDAD = 0.45  # fracción de poros de un suelo medio
ALMACEN_MM = PROFUNDIDAD_MM * POROSIDAD  # agua que cabe a 100 % de saturación
MINIMO_PCT = 5.0
DIAS_REALES = 14  # días de POWER que se piden (los últimos con dato se usan para calibrar)
DIAS_CALIBRAR = 7
DIAS_PASADOS = 14  # días anteriores que se piden a Open-Meteo: cubren el retraso de POWER y la calibración
DIAS_PRONOSTICO = 7  # hoy y los 6 siguientes
FACTOR_ET_DEFECTO = 0.6  # si no se puede calibrar (sin evaporación real o ET0)
FACTOR_ET_MIN, FACTOR_ET_MAX = 0.2, 1.5
UMBRAL_LLUVIA_FUERTE_MM = 20  # mismo umbral del índice R20mm (ETCCDI/OMM) que usa /erosion
CAMBIO_ESTABLE_PTS = 1.0  # menos que esto en la semana se llama "estable"
SEGUNDOS_CACHE = 3 * 3600

_cache: dict[tuple, tuple[float, dict]] = {}


class ErrorProyeccion(Exception):
    """No hay con qué proyectar (sin dato real de POWER o el pronóstico no respondió)."""


def _iso(fecha_power: str) -> str:
    """'20261112' -> '2026-11-12'."""
    return f"{fecha_power[:4]}-{fecha_power[4:6]}-{fecha_power[6:]}"


def _medias_por_dia(horas: list[str], valores: list) -> dict[str, float]:
    """Promedio diario de una serie por hora ('2026-11-15T13:00' -> fecha)."""
    acumulado: dict[str, list[float]] = {}
    for h, v in zip(horas, valores):
        if v is not None:
            acumulado.setdefault(h[:10], []).append(v)
    return {f: sum(v) / len(v) for f, v in acumulado.items()}


def _promedio(valores: list[float]) -> float | None:
    return sum(valores) / len(valores) if valores else None


def proyectar(real: list[dict], om: dict, dias_pasados: int = DIAS_PASADOS) -> dict:
    """Arma la proyección con los días reales de POWER (`nasa_power.diario`) y la respuesta de Open-Meteo.

    Es una función pura (sin red) para poder probarla. `om["daily"]["time"][dias_pasados]` es hoy.
    """
    validos = [r for r in real if r.get("humedad_raiz") is not None]
    if not validos:
        raise ErrorProyeccion("NASA POWER has no recent data for this point")
    ultimo = validos[-1]
    fecha_ultimo = _iso(ultimo["fecha"])

    try:
        diario = om["daily"]
        fechas = diario["time"]
        hoy = fechas[dias_pasados]
        lluvia = dict(zip(fechas, diario["precipitation_sum"]))
        et0 = dict(zip(fechas, diario["et0_fao_evapotranspiration"]))
        temp_om = _medias_por_dia(om["hourly"]["time"], om["hourly"]["soil_temperature_0cm"])
    except (KeyError, IndexError, TypeError) as e:
        raise ErrorProyeccion(f"Open-Meteo sent an unexpected answer ({type(e).__name__})") from e

    # Calibración con los últimos días en que hay dato real y pronóstico/análisis del mismo día
    recientes = [r for r in validos if _iso(r["fecha"]) in et0][-DIAS_CALIBRAR:]
    evaporacion = [r["evaporacion_mm_dia"] for r in recientes if r["evaporacion_mm_dia"] is not None and et0.get(_iso(r["fecha"])) is not None]
    referencia = [et0[_iso(r["fecha"])] for r in recientes if r["evaporacion_mm_dia"] is not None and et0.get(_iso(r["fecha"])) is not None]
    factor = FACTOR_ET_DEFECTO
    if referencia and sum(referencia) > 0:
        factor = min(FACTOR_ET_MAX, max(FACTOR_ET_MIN, sum(evaporacion) / sum(referencia)))
    perdida_media = _promedio(evaporacion)  # respaldo para un día sin ET0

    diferencias = [r["temperatura_suelo"] - temp_om[_iso(r["fecha"])] for r in recientes
                   if r.get("temperatura_suelo") is not None and _iso(r["fecha"]) in temp_om]
    ajuste_temp = _promedio(diferencias) or 0.0

    almacen = ultimo["humedad_raiz"] / 100 * ALMACEN_MM
    filas = []
    for fecha in fechas:
        if fecha <= fecha_ultimo:
            continue
        mm = lluvia.get(fecha)
        et = et0.get(fecha)
        perdida = factor * et if et is not None else (perdida_media or 0.0)
        almacen = min(ALMACEN_MM, max(MINIMO_PCT / 100 * ALMACEN_MM, almacen + (mm or 0.0) - perdida))
        t = temp_om.get(fecha)
        filas.append({
            "fecha": fecha,
            "pasado": fecha < hoy,  # entre el último dato de POWER y hoy: ya ocurrió, pero POWER aún no lo trae
            "humedad_raiz": round(almacen / ALMACEN_MM * 100, 1),
            "temperatura_suelo": None if t is None else round(t + ajuste_temp, 1),
            "evaporacion_mm_dia": round(perdida, 2),
            "lluvia_mm": None if mm is None else round(mm, 1),
        })
    if not filas:
        raise ErrorProyeccion("The forecast has no days after the last real data")

    proximos = [f for f in filas if f["fecha"] >= hoy]
    en_hoy = next((f for f in filas if f["fecha"] == hoy), None)
    humedad_hoy = en_hoy["humedad_raiz"] if en_hoy else ultimo["humedad_raiz"]
    humedad_fin = filas[-1]["humedad_raiz"]
    cambio = round(humedad_fin - humedad_hoy, 1)
    temps = [f["temperatura_suelo"] for f in proximos if f["temperatura_suelo"] is not None]
    fuerte = next((f for f in proximos if (f["lluvia_mm"] or 0) >= UMBRAL_LLUVIA_FUERTE_MM), None)

    return {
        "ultimo_dato_real": fecha_ultimo,
        "hoy": hoy,
        "real": [
            {"fecha": _iso(r["fecha"]), "humedad_raiz": r["humedad_raiz"], "temperatura_suelo": r["temperatura_suelo"],
             "evaporacion_mm_dia": r["evaporacion_mm_dia"]}
            for r in validos
        ],
        "proyeccion": filas,
        "resumen": {
            "humedad_raiz_hoy": humedad_hoy,
            "humedad_raiz_final": humedad_fin,
            "fecha_final": filas[-1]["fecha"],
            "cambio_pts": cambio,
            "tendencia": "sube" if cambio > CAMBIO_ESTABLE_PTS else "baja" if cambio < -CAMBIO_ESTABLE_PTS else "estable",
            "lluvia_total_mm": round(sum(f["lluvia_mm"] or 0 for f in proximos), 1),
            "dias_con_lluvia": sum(1 for f in proximos if (f["lluvia_mm"] or 0) >= 1),
            "perdida_total_mm": round(sum(f["evaporacion_mm_dia"] for f in proximos), 1),
            "temperatura_suelo_min": min(temps) if temps else None,
            "temperatura_suelo_max": max(temps) if temps else None,
            "lluvia_fuerte": None if fuerte is None else {"fecha": fuerte["fecha"], "mm": fuerte["lluvia_mm"]},
        },
        "supuestos": {
            "profundidad_mm": PROFUNDIDAD_MM,
            "porosidad": POROSIDAD,
            "almacen_mm": ALMACEN_MM,
            "factor_evaporacion": round(factor, 2),
            "ajuste_temperatura_c": round(ajuste_temp, 1),
            "umbral_lluvia_fuerte_mm": UMBRAL_LLUVIA_FUERTE_MM,
        },
        "metodo": "Water balance: forecast rain minus evaporation, starting from the last NASA POWER value (FAO Irrigation and Drainage Paper 56)",
        "fuente": "NASA POWER (last real values) + Open-Meteo (rain, FAO reference evapotranspiration, soil temperature)",
    }


async def proyeccion(lat: float, lon: float) -> dict:
    llave = (round(lat, 2), round(lon, 2))
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    hoy = date.today()
    real = await nasa_power.diario(lat, lon, hoy - timedelta(days=DIAS_REALES), hoy)
    try:
        om = await openmeteo._pedir({
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "past_days": DIAS_PASADOS,
            "forecast_days": DIAS_PRONOSTICO,
            "daily": "precipitation_sum,et0_fao_evapotranspiration",
            "hourly": "soil_temperature_0cm",
        })
    except OpenMeteoError as e:
        raise ErrorProyeccion(str(e)) from e
    resultado = {**proyectar(real, om), "actualizado": datetime.now(timezone.utc).isoformat()}
    _cache[llave] = (time.monotonic(), resultado)
    return resultado
