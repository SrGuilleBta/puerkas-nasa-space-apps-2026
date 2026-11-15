"""NASA MODIS por punto, desde NASA Earthdata (LP DAAC) con OPeNDAP:

- Cobertura vegetal y épocas de suelo desnudo: NDVI de MOD13Q1 v061 (250 m, cada 16 días).
- Tipo de cobertura del terreno (cultivo, ciudad, bosque...): MCD12Q1 v061 (500 m, anual, clases IGBP).

Antes se usaba el servicio de recortes del ORNL DAAC, pero era muy lento (30-60 s por consulta) y
pasó caído buena parte del 14-15 nov 2026. Por Earthdata cada fecha tarda ~2 s y usa el mismo
EARTHDATA_TOKEN que SMAP/SRTM/GRACE. Verificado: da el mismo NDVI que el ORNL (0.666 en NL, 16-oct-2026).

- MODIS usa la cuadrícula sinusoidal (mosaicos h/v de ~1112 km). El mosaico y el píxel se calculan
  con la proyección oficial (esfera de radio 6371007.181 m).
- NDVI va de -1 a 1 (viene x10000); -3000 = sin dato.
- Clases de cobertura vegetal según el USGS: NDVI <= 0.1 = suelo desnudo (roca, arena); 0.2-0.3 =
  matorral y pastizal; 0.6-0.8 = bosque. https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index
- Se guarda en disco (backend/data/suelo/modis/): las fechas pasadas no cambian.
"""

import asyncio
import json
import math
import os
from datetime import date
from pathlib import Path

import httpx

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
OPENDAP = "https://opendap.earthdata.nasa.gov/collections/{c}/granules/{g}.dap.csv"
COLECCION_NDVI = "C1748066515-LPCLOUD"  # MOD13Q1 v061
VAR_NDVI = "/MODIS_Grid_16DAY_250m_500m_VI/Data_Fields/_250m_16_days_NDVI"
COLECCION_LC = "C2484079608-LPCLOUD"  # MCD12Q1 v061
VAR_LC = "/MCD12Q1/Data_Fields/LC_Type1"
CARPETA = Path(__file__).resolve().parents[3] / "data" / "suelo" / "modis"
CONSULTAS_SIMULTANEAS = 16
MESES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Cuadrícula sinusoidal de MODIS
_R = 6371007.181
_MOSAICO = 1111950.5197665233
_X0 = -20015109.354
_Y0 = 10007554.677

# Clases IGBP de MCD12Q1 (LC_Type1)
CLASES_IGBP = {
    1: "bosque", 2: "bosque", 3: "bosque", 4: "bosque", 5: "bosque",
    6: "matorral", 7: "matorral", 8: "sabana", 9: "sabana", 10: "pastizal",
    11: "humedal", 12: "cultivo", 13: "ciudad", 14: "mosaico de cultivo y vegetación natural",
    15: "nieve o hielo", 16: "suelo desnudo", 17: "agua",
}


def pixel_sinusoidal(lat: float, lon: float, pixeles: int) -> tuple[int, int, int, int]:
    """(h, v, fila, columna) del píxel que contiene el punto, para mosaicos de `pixeles` × `pixeles`."""
    x = _R * math.radians(lon) * math.cos(math.radians(lat))
    y = _R * math.radians(lat)
    h = int((x - _X0) // _MOSAICO)
    v = int((_Y0 - y) // _MOSAICO)
    celda = _MOSAICO / pixeles
    col = int((x - (_X0 + h * _MOSAICO)) // celda)
    fila = int(((_Y0 - v * _MOSAICO) - y) // celda)
    return h, v, fila, col


def _token() -> str:
    token = os.getenv("EARTHDATA_TOKEN")
    if not token:
        raise RuntimeError("EARTHDATA_TOKEN is missing in .env (needed for MODIS)")
    return token


async def _granulos(cliente: httpx.AsyncClient, coleccion: str, lat: float, lon: float, mosaico: str,
                    inicio: str, fin: str) -> dict[str, str]:
    """{fecha: gránulo} del mosaico que contiene el punto (CMR a veces regresa también el vecino)."""
    salida: dict[str, str] = {}
    pagina = 1
    while True:
        r = await cliente.get(CMR, params={
            "collection_concept_id": coleccion,
            "point": f"{lon},{lat}",
            "temporal": f"{inicio}T00:00:00Z,{fin}T23:59:59Z",
            "sort_key": "-start_date",
            "page_size": 200,
            "page_num": pagina,
        })
        r.raise_for_status()
        entradas = r.json()["feed"]["entry"]
        for g in entradas:
            if f".{mosaico}." in g["title"]:
                salida.setdefault(g["time_start"][:10], g["title"])
        if len(entradas) < 200:
            return salida
        pagina += 1


async def _pixel(cliente: httpx.AsyncClient, coleccion: str, granulo: str, var: str, fila: int, col: int,
                 maximo: int) -> int | None:
    # Ventana de 3×3 (OPeNDAP no devuelve bien un solo valor); se usa el centro
    f0, c0 = max(0, fila - 1), max(0, col - 1)
    f1, c1 = min(maximo - 1, fila + 1), min(maximo - 1, col + 1)
    r = await cliente.get(
        OPENDAP.format(c=coleccion, g=granulo),
        params={"dap4.ce": f"{var}[{f0}:1:{f1}][{c0}:1:{c1}]"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    r.raise_for_status()
    filas = [ln.partition(",")[2] for ln in r.text.splitlines()[1:] if "[" in ln]
    valores = [[int(float(v)) for v in f.split(",") if v.strip()] for f in filas]
    return valores[fila - f0][col - c0]


# ---------- NDVI (cobertura vegetal) ----------

def clase_usgs(ndvi: float) -> str:
    if ndvi <= 0.1:
        return "bare soil"
    if ndvi < 0.2:
        return "very sparse vegetation"
    if ndvi <= 0.3:
        return "shrubland or grassland"
    if ndvi < 0.6:
        return "moderate vegetation"
    return "dense vegetation"


# Calidad del píxel (pixel reliability de MOD13Q1): 0 bueno, 1 marginal, 2 nieve/hielo, 3 nublado,
# -1 sin dato. Solo se usan 0 y 1 (guía de usuario de MOD13, Didan et al. 2015): las nubes bajan el
# NDVI y harían ver "suelo desnudo" donde no lo hay (pasó en Monterrey el 16-oct-2026:
# NDVI 0.236 con píxel nublado, contra 0.696 dos semanas antes).
VAR_CALIDAD = "/MODIS_Grid_16DAY_250m_500m_VI/Data_Fields/_250m_16_days_pixel_reliability"
CALIDAD_BUENA = (0, 1)
# capa: (variable en Earthdata, conversión del valor crudo)
CAPAS = {
    "ndvi": (VAR_NDVI, lambda v: None if v is None or v <= -3000 else round(v * 0.0001, 3)),
    "calidad": (VAR_CALIDAD, lambda v: None if v is None or v < 0 else int(v)),
}


def _archivo(lat: float, lon: float, capa: str = "ndvi") -> Path:
    return CARPETA / f"{capa}_{lat:.4f}_{lon:.4f}.json"


def _leer_cache(lat: float, lon: float, capa: str = "ndvi") -> dict:
    archivo = _archivo(lat, lon, capa)
    return json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}


def _leer_caches(lat: float, lon: float) -> dict[str, dict]:
    return {capa: _leer_cache(lat, lon, capa) for capa in CAPAS}


def _guardar_caches(lat: float, lon: float, caches: dict[str, dict]) -> None:
    # Se junta con lo que ya está en disco por si dos consultas del mismo punto corren al mismo
    # tiempo: sin esto, la última en guardar borraría lo que bajó la otra.
    CARPETA.mkdir(parents=True, exist_ok=True)
    for capa, cache in caches.items():
        junto = {**_leer_cache(lat, lon, capa), **cache}
        _archivo(lat, lon, capa).write_text(json.dumps(junto, sort_keys=True), encoding="utf-8")


def _buenos(caches: dict[str, dict], fechas) -> dict[str, float]:
    """{fecha: ndvi} solo de las fechas con NDVI y calidad buena o marginal."""
    return {f: caches["ndvi"][f] for f in fechas
            if caches["ndvi"].get(f) is not None and caches["calidad"].get(f) in CALIDAD_BUENA}


async def _llenar(cliente: httpx.AsyncClient, granulos: dict[str, str], caches: dict[str, dict],
                  fila: int, col: int) -> list:
    """Pide a Earthdata el NDVI y la calidad que falten en `caches`. Devuelve los errores."""
    semaforo = asyncio.Semaphore(CONSULTAS_SIMULTANEAS)

    async def una(fecha: str, granulo: str, capa: str):
        var, convertir = CAPAS[capa]
        async with semaforo:
            caches[capa][fecha] = convertir(await _pixel(cliente, COLECCION_NDVI, granulo, var, fila, col, 4800))

    tareas = [una(f, g, capa) for f, g in granulos.items() for capa in CAPAS if f not in caches[capa]]
    resultados = await asyncio.gather(*tareas, return_exceptions=True)
    return [x for x in resultados if isinstance(x, Exception)]


async def _serie(lat: float, lon: float, anios: int) -> dict[str, float | None]:
    """{fecha: ndvi} de los últimos `anios` años completos más el año en curso. Las fechas con nubes,
    nieve o sin dato vienen en None."""
    caches = _leer_caches(lat, lon)
    inicio = f"{date.today().year - anios}-01-01"
    h, v, fila, col = pixel_sinusoidal(lat, lon, 4800)
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cliente:
            granulos = await _granulos(cliente, COLECCION_NDVI, lat, lon, f"h{h:02d}v{v:02d}",
                                       inicio, date.today().isoformat())
            errores = await _llenar(cliente, granulos, caches, fila, col)
    except httpx.HTTPError as e:
        raise RuntimeError("MODIS (NASA Earthdata) did not respond. Please try again in a moment.") from e
    _guardar_caches(lat, lon, caches)
    fechas = [f for f in caches["ndvi"] if f >= inicio]
    if not fechas and errores:
        raise RuntimeError("MODIS (NASA Earthdata) did not respond. Please try again in a moment.")
    buenos = _buenos(caches, fechas)
    return {f: buenos.get(f) for f in fechas}


async def cobertura(lat: float, lon: float, anios: int = 3) -> dict:
    serie = await _serie(lat, lon, anios)
    validos = {f: v for f, v in serie.items() if v is not None}
    por_mes: dict[int, list[float]] = {}
    for f, v in validos.items():
        if int(f[:4]) < date.today().year:  # solo años completos para el promedio por mes
            por_mes.setdefault(int(f[5:7]), []).append(v)
    meses = []
    for m in range(1, 13):
        vals = por_mes.get(m, [])
        prom = round(sum(vals) / len(vals), 3) if vals else None
        meses.append({"mes": MESES[m - 1], "ndvi_promedio": prom, "clase": clase_usgs(prom) if prom is not None else None})
    ultimos = sorted(validos.items())[-23:]  # ~1 año (una imagen cada 16 días)
    ultimo = ultimos[-1] if ultimos else None
    con_dato = [m for m in meses if m["ndvi_promedio"] is not None]
    return {
        "ultimo": {"fecha": ultimo[0], "ndvi": ultimo[1], "clase": clase_usgs(ultimo[1])} if ultimo else None,
        "promedio_por_mes": meses,
        "meses_suelo_desnudo": [m["mes"] for m in con_dato if m["ndvi_promedio"] <= 0.1],
        "mes_menor_cobertura": min(con_dato, key=lambda m: m["ndvi_promedio"]) if con_dato else None,
        "serie_ultimo_anio": [{"fecha": f, "ndvi": v} for f, v in ultimos],
        "anios_promediados": f"{date.today().year - anios}-{date.today().year - 1}",
        "metodo": "USGS classes: NDVI <= 0.1 bare soil; 0.2-0.3 shrubland/grassland; >= 0.6 dense vegetation. "
                  "Only pixels with good or marginal quality (no clouds or snow)",
        "fuente": "NASA MODIS MOD13Q1 v061 (NDVI, 250 m, 16 días) vía NASA Earthdata",
    }


# ---------- Tipo de cobertura del terreno (para verificar que un punto sea cultivo) ----------

async def tipo_cobertura(lat: float, lon: float) -> dict:
    """Clase IGBP del píxel de 500 m que contiene el punto, del año más reciente de MCD12Q1."""
    h, v, fila, col = pixel_sinusoidal(lat, lon, 2400)
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cliente:
            hoy = date.today()
            granulos = await _granulos(cliente, COLECCION_LC, lat, lon, f"h{h:02d}v{v:02d}",
                                       f"{hoy.year - 4}-01-01", hoy.isoformat())
            if not granulos:
                raise RuntimeError("MCD12Q1 no tiene mapa para este punto")
            anio = max(granulos)
            clase = await _pixel(cliente, COLECCION_LC, granulos[anio], VAR_LC, fila, col, 2400)
    except httpx.HTTPError as e:
        raise RuntimeError("MODIS (NASA Earthdata) did not respond. Please try again in a moment.") from e
    return {
        "clase_igbp": clase,
        "cobertura": CLASES_IGBP.get(clase, "sin dato"),
        "es_cultivo": clase in (12, 14),
        "anio": anio[:4],
        "fuente": "NASA MODIS MCD12Q1 v061 (500 m, clases IGBP)",
    }


# ---------- Punto de cultivo más cercano (para lugares que agrega el usuario) ----------
# Las ubicaciones de inicio ya traen su punto de suelo (db.py). Para un lugar nuevo se busca el píxel
# de CULTIVO más cercano según MCD12Q1 (clases IGBP 12 y 14), primero a ~25 km y luego a ~50 km.
# Una sola consulta por lugar; el resultado se guarda en backend/data/suelo/cultivo_cercano.json.

CULTIVO = (12, 14)
RADIOS_CULTIVO = [50, 100]  # en píxeles de 500 m: ~25 km y ~50 km
ARCHIVO_CULTIVO = CARPETA.parent / "cultivo_cercano.json"


def _lat_lon_de_pixel(h: int, v: int, fila: int, col: int, pixeles: int) -> tuple[float, float]:
    celda = _MOSAICO / pixeles
    x = _X0 + h * _MOSAICO + (col + 0.5) * celda
    y = _Y0 - v * _MOSAICO - (fila + 0.5) * celda
    lat = math.degrees(y / _R)
    lon = math.degrees(x / (_R * math.cos(math.radians(lat))))
    return round(lat, 4), round(lon, 4)


async def cultivo_cercano(lat: float, lon: float) -> dict | None:
    """{lat, lon, km, clase} del píxel de cultivo más cercano, o None si no hay a ~50 km."""
    clave = f"{lat:.4f},{lon:.4f}"
    guardados = json.loads(ARCHIVO_CULTIVO.read_text(encoding="utf-8")) if ARCHIVO_CULTIVO.exists() else {}
    if clave in guardados:
        return guardados[clave]
    n = 2400
    h, v, fila, col = pixel_sinusoidal(lat, lon, n)
    hoy = date.today()
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as cliente:
        granulos = await _granulos(cliente, COLECCION_LC, lat, lon, f"h{h:02d}v{v:02d}",
                                   f"{hoy.year - 4}-01-01", hoy.isoformat())
        if not granulos:
            return None
        granulo = granulos[max(granulos)]
        resultado = None
        for radio in RADIOS_CULTIVO:
            f0, f1 = max(0, fila - radio), min(n - 1, fila + radio)
            c0, c1 = max(0, col - radio), min(n - 1, col + radio)
            r = await cliente.get(
                OPENDAP.format(c=COLECCION_LC, g=granulo),
                params={"dap4.ce": f"{VAR_LC}[{f0}:1:{f1}][{c0}:1:{c1}]"},
                headers={"Authorization": f"Bearer {_token()}"},
            )
            r.raise_for_status()
            filas = [ln.partition(",")[2] for ln in r.text.splitlines()[1:] if "[" in ln]
            mejor = None
            for i, linea in enumerate(filas):
                for j, valor in enumerate(linea.split(",")):
                    if valor.strip() and int(float(valor)) in CULTIVO:
                        d = math.hypot(f0 + i - fila, c0 + j - col)
                        if mejor is None or d < mejor[0]:
                            mejor = (d, f0 + i, c0 + j, int(float(valor)))
            if mejor:
                la, lo = _lat_lon_de_pixel(h, v, mejor[1], mejor[2], n)
                resultado = {"lat": la, "lon": lo, "km": round(mejor[0] * _MOSAICO / n / 1000, 1),
                             "clase": CLASES_IGBP[mejor[3]]}
                break
    guardados[clave] = resultado
    ARCHIVO_CULTIVO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_CULTIVO.write_text(json.dumps(guardados, ensure_ascii=False, indent=1), encoding="utf-8")
    return resultado
