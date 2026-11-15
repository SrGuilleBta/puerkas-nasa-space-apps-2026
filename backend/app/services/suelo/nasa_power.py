"""Datos de suelo de NASA POWER: humedad (superficie, raíz, perfil), temperatura del suelo,
evaporación y lluvias fuertes (para erosión).

Notas de la fuente:
- Humedad viene como fracción de 0 a 1 (la devolvemos en %).
- -999 significa "sin dato" (los últimos 2-3 días casi siempre vienen así).
- La serie mensual trae un "mes 13" que es el promedio del año: se descarta.
- Resolución ~50 km: sirve para la región, no para una parcela exacta.
"""

from datetime import date, timedelta

import httpx

URL_DIARIO = "https://power.larc.nasa.gov/api/temporal/daily/point"
URL_MENSUAL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

VARIABLES = {
    "GWETTOP": "humedad_superficie",
    "GWETROOT": "humedad_raiz",
    "GWETPROF": "humedad_perfil",
    "TS": "temperatura_suelo",
    "EVLAND": "evaporacion_mm_dia",
}
HUMEDADES = {"GWETTOP", "GWETROOT", "GWETPROF"}

_cache: dict[tuple, dict] = {}


def _limpiar(var: str, valor: float) -> float | None:
    if valor is None or valor <= -999:
        return None
    if var in HUMEDADES:
        return round(valor * 100, 1)
    return round(valor, 2)


async def _consultar(url: str, lat: float, lon: float, inicio: str, fin: str, variables=VARIABLES) -> dict:
    clave = (url, round(lat, 3), round(lon, 3), inicio, fin, tuple(variables))
    if clave in _cache:
        return _cache[clave]
    params = {
        "parameters": ",".join(variables),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": inicio,
        "end": fin,
        "format": "JSON",
    }
    async with httpx.AsyncClient(timeout=60) as cliente:
        r = await cliente.get(url, params=params)
        r.raise_for_status()
        datos = r.json()["properties"]["parameter"]
    _cache[clave] = datos
    return datos


def _por_fecha(datos: dict, quitar_mes_13: bool = False) -> list[dict]:
    """Convierte {variable: {fecha: valor}} en [{fecha, humedad_superficie, ...}]."""
    fechas = sorted(next(iter(datos.values())).keys())
    filas = []
    for f in fechas:
        if quitar_mes_13 and f.endswith("13"):
            continue
        fila = {"fecha": f}
        for var, nombre in VARIABLES.items():
            fila[nombre] = _limpiar(var, datos.get(var, {}).get(f))
        filas.append(fila)
    return filas


async def diario(lat: float, lon: float, inicio: date, fin: date) -> list[dict]:
    datos = await _consultar(URL_DIARIO, lat, lon, inicio.strftime("%Y%m%d"), fin.strftime("%Y%m%d"))
    return _por_fecha(datos)


async def mensual(lat: float, lon: float, anio_inicio: int, anio_fin: int) -> list[dict]:
    datos = await _consultar(URL_MENSUAL, lat, lon, str(anio_inicio), str(anio_fin))
    return _por_fecha(datos, quitar_mes_13=True)


async def actual(lat: float, lon: float) -> dict | None:
    """Último día con datos completos (POWER tiene 2-3 días de retraso)."""
    hoy = date.today()
    filas = await diario(lat, lon, hoy - timedelta(days=14), hoy)
    for fila in reversed(filas):
        if fila["humedad_raiz"] is not None:
            return fila
    return None


# El estado de sequía ya no se calcula con NASA POWER: el 1-oct-2026 POWER cambió de modelo
# (MERRA-2 -> GEOS-IT) y comparar el dato nuevo contra el historial viejo daba sequías falsas
# (Yucatán salía D4 y el Monitor de Sequía de CONAGUA decía "sin sequía"). Ahora se usa SMAP
# (services/suelo/smap.py), que mide con el mismo instrumento desde 2015.


async def lluvias_fuertes(lat: float, lon: float, anios: int = 10, umbral_mm: float = 20) -> dict:
    """Días por año con lluvia >= 20 mm: índice R20mm ("días de precipitación muy intensa") del
    ETCCDI (OMM). https://etccdi.pacificclimate.org/list_27_indices.shtml"""
    fin = date(date.today().year - 1, 12, 31)
    inicio = date(fin.year - anios + 1, 1, 1)
    datos = await _consultar(URL_DIARIO, lat, lon, inicio.strftime("%Y%m%d"), fin.strftime("%Y%m%d"), ["PRECTOTCORR"])
    valores = [v for v in datos["PRECTOTCORR"].values() if v is not None and v > -999]
    fuertes = [v for v in valores if v >= umbral_mm]
    return {
        "dias_por_anio": round(len(fuertes) / anios, 1),
        "lluvia_maxima_dia_mm": round(max(valores), 1) if valores else None,
        "umbral_mm": umbral_mm,
        "indice": "R20mm (ETCCDI/OMM)",
        "periodo": f"{inicio.year}-{fin.year}",
    }


async def lluvia_diaria(lat: float, lon: float, inicio: date, fin: date) -> dict[str, float | None]:
    """{AAAA-MM-DD: lluvia en mm} (solo se muestra, no se compara contra el historial)."""
    datos = await _consultar(URL_DIARIO, lat, lon, inicio.strftime("%Y%m%d"), fin.strftime("%Y%m%d"), ["PRECTOTCORR"])
    return {
        f"{f[:4]}-{f[4:6]}-{f[6:]}": (round(v, 1) if v is not None and v > -999 else None)
        for f, v in datos["PRECTOTCORR"].items()
    }
