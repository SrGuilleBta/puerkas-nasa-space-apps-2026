"""Cliente de Meteomatics (https://www.meteomatics.com) para la pantalla Principal.

Los valores diarios `*_24h` de Meteomatics cubren las 24 horas ANTERIORES a la fecha pedida,
así que para el día local D se pide la marca de las 00:00 locales de D+1.
"""

import asyncio
import time
from datetime import datetime, time as hora, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from app import config
from app.services.ubicaciones import Ubicacion

BASE = "https://api.meteomatics.com"
SEGUNDOS_CACHE = 600  # 10 minutos: la API cobra por consulta y el clima no cambia tan rápido

_cache: dict[str, tuple[float, dict]] = {}

DIARIOS = [
    "t_max_2m_24h:C",
    "t_min_2m_24h:C",
    "prob_precip_24h:p",
    "weather_symbol_24h:idx",
]
AHORA = [
    "t_2m:C",
    "t_apparent:C",
    "relative_humidity_2m:p",
    "wind_speed_10m:kmh",
    "weather_symbol_1h:idx",
    "soil_moisture_index_-10cm:idx",
]

# Símbolos de Meteomatics (los de noche suman 100, por eso se usa % 100)
TEXTO_CIELO = {
    1: "Clear",
    2: "Mostly clear",
    3: "Partly cloudy",
    4: "Cloudy",
    5: "Rain",
    6: "Rain and snow",
    7: "Snow",
    8: "Showers",
    9: "Snow showers",
    10: "Sleet",
    11: "Mist",
    12: "Dense fog",
    13: "Freezing rain",
    14: "Thunderstorm",
    15: "Drizzle",
    16: "Sandstorm",
}


class MeteomaticsError(Exception):
    pass


class SinCredenciales(MeteomaticsError):
    pass


def _icono(simbolo: float | None) -> str:
    """Tipo de icono para el frontend: sol, nube o lluvia."""
    if simbolo is None:
        return "nube"
    s = int(simbolo) % 100
    if s in (1, 2):
        return "sol"
    if s in (3, 4, 11, 12):
        return "nube"
    return "lluvia"


def _texto(simbolo: float | None) -> str | None:
    return None if simbolo is None else TEXTO_CIELO.get(int(simbolo) % 100)


def _redondear(valor: float | None, decimales: int = 0):
    if valor is None:
        return None
    r = round(valor, decimales)
    return int(r) if decimales == 0 else r


async def _consultar(cliente: httpx.AsyncClient, fecha: str, parametros: list[str], m: Ubicacion):
    url = f"{BASE}/{fecha}/{','.join(parametros)}/{m.lat},{m.lon}/json"
    try:
        r = await cliente.get(url, auth=(config.METEOMATICS_USER, config.METEOMATICS_PASSWORD))
    except httpx.HTTPError as e:
        raise MeteomaticsError(f"Could not connect to Meteomatics ({type(e).__name__})") from e
    if r.status_code == 401:
        raise MeteomaticsError("Meteomatics rejected the username or password")
    if r.status_code >= 400:
        raise MeteomaticsError(f"Meteomatics responded with {r.status_code}")
    datos = r.json()["data"]
    return {
        p["parameter"]: [d["value"] for d in p["coordinates"][0]["dates"]] for p in datos
    }


def _utc(dia, zona: ZoneInfo) -> str:
    """Las 00:00 locales de `dia`, en el formato que pide Meteomatics."""
    local = datetime.combine(dia, hora.min, tzinfo=zona)
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _optimo_para_campo(temp, viento, prob_lluvia) -> bool | None:
    if None in (temp, viento, prob_lluvia):
        return None
    return 10 <= temp <= 35 and viento < 25 and prob_lluvia < 30


async def clima(m: Ubicacion) -> dict:
    if not config.METEOMATICS_USER or not config.METEOMATICS_PASSWORD:
        raise SinCredenciales("METEOMATICS_USER and METEOMATICS_PASSWORD are missing from .env")

    llave = f"{m.lat:.3f},{m.lon:.3f}"  # por coordenadas: "Mi ubicación" cambia de lugar con el mismo nombre
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < SEGUNDOS_CACHE:
        return guardado[1]

    zona = ZoneInfo(m.zona)
    hoy_local = datetime.now(zona).date()
    # Marcas "fin de día" de hoy a dentro de 6 días: mañana 00:00 ... hoy + 7 días 00:00
    rango = f"{_utc(hoy_local + timedelta(days=1), zona)}--{_utc(hoy_local + timedelta(days=7), zona)}:P1D"

    async with httpx.AsyncClient(timeout=20) as cliente:
        diarios, ahora = await asyncio.gather(
            _consultar(cliente, rango, DIARIOS, m),
            _consultar(cliente, "now", AHORA, m),
        )

    pronostico = []
    for i in range(7):
        pronostico.append(
            {
                "fecha": (hoy_local + timedelta(days=i)).isoformat(),
                "tmax": _redondear(diarios["t_max_2m_24h:C"][i]),
                "tmin": _redondear(diarios["t_min_2m_24h:C"][i]),
                "lluvia": _redondear(diarios["prob_precip_24h:p"][i]),
                "cielo": _icono(diarios["weather_symbol_24h:idx"][i]),
            }
        )

    primero = lambda nombre: ahora[nombre][0]
    temperatura = primero("t_2m:C")
    viento = primero("wind_speed_10m:kmh")
    humedad_suelo = primero("soil_moisture_index_-10cm:idx")
    simbolo = primero("weather_symbol_1h:idx")
    prob_hoy = pronostico[0]["lluvia"]

    resultado = {
        "municipio": m.nombre,
        "fuente": "Meteomatics",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "pronostico": pronostico,
        "hoy": {
            "temperatura": _redondear(temperatura),
            "sensacion": _redondear(primero("t_apparent:C")),
            "cielo": _texto(simbolo),
            "icono": _icono(simbolo),
            "optimoParaCampo": _optimo_para_campo(temperatura, viento, prob_hoy),
            "humedad": _redondear(primero("relative_humidity_2m:p")),
            "vientoKmh": _redondear(viento),
            "humedadSuelo": None if humedad_suelo is None else _redondear(humedad_suelo * 100),
            "phSuelo": None,  # Meteomatics no lo da: lo agrega el router con SoilGrids
        },
    }
    _cache[llave] = (time.monotonic(), resultado)
    return resultado
