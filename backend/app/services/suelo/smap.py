"""Humedad superficial del suelo MEDIDA por satélite: NASA SMAP L3 Enhanced (SPL3SMP_E, 9 km, diario).

A diferencia de NASA POWER (que es un modelo), SMAP mide la humedad de los primeros ~5 cm con un
radiómetro de microondas, siempre con el mismo instrumento desde 2015. Por eso se usa también para
el estado de sequía: NASA POWER cambió de modelo el 1-oct-2026 (MERRA-2 -> GEOS-IT) y comparar el
dato nuevo contra el historial viejo daba sequías falsas.

- Cada archivo diario pesa ~600 MB, así que no se descarga: se pide solo el píxel del punto con
  OPeNDAP de Earthdata (~1-2 s por día). Requiere EARTHDATA_TOKEN en .env.
- Las mediciones ya consultadas se guardan en backend/data/suelo/smap/ (los datos de días pasados
  no cambian). Precarga de los 32 estados: `python -m scripts.precargar_smap`.
- Unidad: m³/m³ (fracción de volumen de agua); se devuelve en % de volumen.
- El satélite pasa dos veces al día (6 am "AM" y 6 pm "PM") y no cubre todo el país cada día.
- `retrieval_qual_flag` bit 0 = 0 significa "calidad recomendada" por el equipo de SMAP. Se reporta.
- Cuadrícula EASE-Grid 2.0 global de 9 km (3856 × 1624). El renglón/columna se calcula con la
  proyección oficial (cilíndrica de áreas iguales, paralelo estándar 30°, elipsoide WGS84).
"""

import asyncio
import json
import math
import os
from datetime import date, timedelta
from pathlib import Path

import httpx

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLECCION = "C2938664763-NSIDC_CPRD"  # SPL3SMP_E v006
OPENDAP = "https://opendap.earthdata.nasa.gov/collections/{c}/granules/{g}.dap.csv"
SIN_DATO = -9999
PRIMER_ANIO = 2015  # SPL3SMP_E empieza el 31-mar-2015
CARPETA = Path(__file__).resolve().parents[3] / "data" / "suelo" / "smap"
CONSULTAS_SIMULTANEAS = 16

# EASE-Grid 2.0, 9 km (NSIDC)
_A = 6378137.0
_E2 = 0.0066943799901413165
_E = math.sqrt(_E2)
_K0 = math.cos(math.radians(30)) / math.sqrt(1 - _E2 * math.sin(math.radians(30)) ** 2)
_CELDA = 9008.055210146
_X0 = -17367530.44516138
_Y0 = 7314540.83097131

_bloqueos: dict[tuple[int, int], asyncio.Lock] = {}


def celda_ease2(lat: float, lon: float) -> tuple[int, int]:
    s = math.sin(math.radians(lat))
    q = (1 - _E2) * (s / (1 - _E2 * s * s) - (1 / (2 * _E)) * math.log((1 - _E * s) / (1 + _E * s)))
    x = _A * _K0 * math.radians(lon)
    y = _A * q / (2 * _K0)
    return int((_Y0 - y) // _CELDA), int((x - _X0) // _CELDA)


def _token() -> str:
    token = os.getenv("EARTHDATA_TOKEN")
    if not token:
        raise RuntimeError("EARTHDATA_TOKEN is missing in .env (needed for SMAP)")
    return token


# ---------- celda a usar ----------
# SMAP deja vacía la celda de 9 km cuando tiene mucha ciudad o agua. Si la celda del punto no tiene
# NINGUNA medición en los últimos 10 días, se usa (siempre la misma) la celda vecina con más
# mediciones, a ~9 km. Se decide una vez y se guarda en backend/data/suelo/smap/celdas.json.

ARCHIVO_CELDAS = CARPETA / "celdas.json"


async def celda_para(lat: float, lon: float) -> tuple[int, int, bool]:
    """(fila, columna, es_vecina) de la celda de SMAP a usar para el punto."""
    fila, col = celda_ease2(lat, lon)
    clave = f"{fila}_{col}"
    elegidas = json.loads(ARCHIVO_CELDAS.read_text(encoding="utf-8")) if ARCHIVO_CELDAS.exists() else {}
    if clave in elegidas:
        f, c = elegidas[clave]
        return f, c, (f, c) != (fila, col)
    hoy = date.today()
    conteo: dict[tuple[int, int], int] = {}
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cliente:
            granulos = await _granulos(cliente, hoy - timedelta(days=10), hoy)
            semaforo = asyncio.Semaphore(CONSULTAS_SIMULTANEAS)

            async def una(g: str):
                async with semaforo:
                    return await _ventana(cliente, g, fila, col)

            for ventana in await asyncio.gather(*(una(g) for g in granulos.values()), return_exceptions=True):
                if isinstance(ventana, dict):
                    for (di, dj), m in ventana.items():
                        if m is not None:
                            conteo[(di, dj)] = conteo.get((di, dj), 0) + 1
    except httpx.HTTPError:
        return fila, col, False  # sin respuesta: se usa la del punto y no se guarda la decisión
    if conteo.get((0, 0)) or not conteo:
        f, c = fila, col
    else:
        # la vecina con más mediciones; si empatan, la más cercana (lados antes que esquinas)
        di, dj = max(conteo, key=lambda k: (conteo[k], -(abs(k[0]) + abs(k[1]))))
        f, c = fila + di, col + dj
    elegidas[clave] = [f, c]
    CARPETA.mkdir(parents=True, exist_ok=True)
    ARCHIVO_CELDAS.write_text(json.dumps(elegidas), encoding="utf-8")
    return f, c, (f, c) != (fila, col)


# ---------- caché en disco por celda: {fecha: medición o null} ----------

def _archivo(fila: int, col: int) -> Path:
    return CARPETA / f"celda_{fila}_{col}.json"


def _leer_cache(fila: int, col: int) -> dict:
    a = _archivo(fila, col)
    return json.loads(a.read_text(encoding="utf-8")) if a.exists() else {}


def _guardar_cache(fila: int, col: int, datos: dict) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    _archivo(fila, col).write_text(json.dumps(datos, sort_keys=True), encoding="utf-8")


# ---------- consultas a NASA ----------

async def _granulos(cliente: httpx.AsyncClient, inicio: date, fin: date) -> dict[str, str]:
    """{fecha AAAA-MM-DD: nombre del gránulo} entre dos fechas (si un día tiene dos versiones,
    se queda la primera que regresa CMR)."""
    salida: dict[str, str] = {}
    pagina = 1
    while True:
        r = await cliente.get(CMR, params={
            "collection_concept_id": COLECCION,
            "temporal": f"{inicio.isoformat()}T00:00:00Z,{fin.isoformat()}T23:59:59Z",
            "sort_key": "-start_date",
            "page_size": 200,
            "page_num": pagina,
        })
        r.raise_for_status()
        entradas = r.json()["feed"]["entry"]
        for g in entradas:
            salida.setdefault(g["time_start"][:10], g["title"])
        if len(entradas) < 200:
            return salida
        pagina += 1


def _leer_csv(texto: str) -> dict[str, list[list[float]]]:
    """Convierte la respuesta CSV de OPeNDAP en {variable: [[fila], ...]}."""
    datos: dict[str, list[list[float]]] = {}
    for linea in texto.splitlines()[1:]:
        if "[" not in linea:
            continue
        nombre, _, valores = linea.partition(",")
        var = nombre.split("/")[-1].split("[")[0]
        fila = [float(v) for v in valores.split(",") if v.strip()]
        datos.setdefault(var, []).append(fila)
    return datos


def _de_celda(d: dict, i: int, j: int) -> dict | None:
    for pasada, sm, flag in (("AM (6 am)", "soil_moisture", "retrieval_qual_flag"),
                             ("PM (6 pm)", "soil_moisture_pm", "retrieval_qual_flag_pm")):
        try:
            valor = d[sm][i][j]
            bandera = int(d[flag][i][j])
        except (KeyError, IndexError):
            continue
        if valor != SIN_DATO and valor >= 0:
            return {
                "humedad_pct_volumen": round(valor * 100, 1),
                "pasada": pasada,
                "calidad_recomendada": (bandera & 1) == 0,
            }
    return None


async def _ventana(cliente: httpx.AsyncClient, granulo: str, fila: int, col: int) -> dict:
    """Mediciones de la ventana de 3×3 alrededor de (fila, col): {(di, dj): medición o None}."""
    v = f"[{fila - 1}:1:{fila + 1}][{col - 1}:1:{col + 1}]"
    am, pm = "/Soil_Moisture_Retrieval_Data_AM", "/Soil_Moisture_Retrieval_Data_PM"
    ce = ";".join([
        f"{am}/soil_moisture{v}", f"{am}/retrieval_qual_flag{v}",
        f"{pm}/soil_moisture_pm{v}", f"{pm}/retrieval_qual_flag_pm{v}",
    ])
    r = await cliente.get(
        OPENDAP.format(c=COLECCION, g=granulo),
        params={"dap4.ce": ce},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    r.raise_for_status()
    d = _leer_csv(r.text)
    return {(i - 1, j - 1): _de_celda(d, i, j) for i in range(3) for j in range(3)}


async def _medicion(cliente: httpx.AsyncClient, granulo: str, fila: int, col: int) -> dict | None:
    # Se pide una ventana de 3×3 (OPeNDAP no devuelve bien un solo valor) y se usa el centro.
    return (await _ventana(cliente, granulo, fila, col))[(0, 0)]


async def serie(lat: float, lon: float, rangos: list[tuple[date, date]]) -> dict[str, dict | None]:
    """Mediciones del punto en uno o varios rangos de fechas: {fecha: medición o None (sin dato)}.
    Usa la caché en disco y solo consulta a NASA los días que faltan."""
    fila, col, _ = await celda_para(lat, lon)
    bloqueo = _bloqueos.setdefault((fila, col), asyncio.Lock())
    async with bloqueo:
        cache = _leer_cache(fila, col)
        hoy = date.today()
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cliente:
                pendientes: dict[str, str] = {}
                for inicio, fin in rangos:
                    dias = {(inicio + timedelta(days=k)).isoformat() for k in range((fin - inicio).days + 1)}
                    if dias <= cache.keys():
                        continue
                    granulos = await _granulos(cliente, inicio, fin)
                    pendientes.update({f: g for f, g in granulos.items() if f not in cache})

                semaforo = asyncio.Semaphore(CONSULTAS_SIMULTANEAS)

                async def una(fecha: str, granulo: str):
                    async with semaforo:
                        return fecha, await _medicion(cliente, granulo, fila, col)

                resultados = await asyncio.gather(
                    *(una(f, g) for f, g in pendientes.items()), return_exceptions=True
                )
        except httpx.HTTPError as e:
            raise RuntimeError("SMAP (NASA Earthdata) did not respond. Please try again in a moment.") from e

        for res in resultados:
            if isinstance(res, tuple):
                fecha, medicion = res
                # Un día sin dato se recuerda como None, salvo los últimos 5 días (NASA puede
                # publicar una versión nueva del archivo).
                if medicion is not None or (hoy - date.fromisoformat(fecha)).days > 5:
                    cache[fecha] = medicion
        _guardar_cache(fila, col, cache)

    salida = {}
    for inicio, fin in rangos:
        for k in range((fin - inicio).days + 1):
            f = (inicio + timedelta(days=k)).isoformat()
            salida[f] = cache.get(f)
    return salida


# ---------- lo que usan los endpoints ----------

async def humedad(lat: float, lon: float, dias: int = 10) -> dict:
    """Mediciones de SMAP de los últimos `dias` días en el punto y la más reciente."""
    hoy = date.today()
    datos = await serie(lat, lon, [(hoy - timedelta(days=dias), hoy)])
    lista = sorted(({"fecha": f, **m} for f, m in datos.items() if m), key=lambda m: m["fecha"])
    fila, col, vecina = await celda_para(lat, lon)
    return {
        "ultima": lista[-1] if lista else None,
        "serie": lista,
        "dias_revisados": dias,
        "celda_9km": {"fila": fila, "columna": col, "vecina": vecina},
        "nota": "Satellite measurement of the top ~5 cm. The satellite does not cover the whole country every day, so some days have no data.",
        "fuente": "NASA SMAP L3 Enhanced (SPL3SMP_E v006), 9 km",
    }


# Cortes por percentil del U.S. Drought Monitor (metodología que comparte el Monitor de Sequía de
# América del Norte: EE. UU., México y Canadá).
# https://droughtmonitor.unl.edu/About/AbouttheData/DroughtClassification.aspx
# OJO: esto mide SOLO la humedad del suelo comparada con otros años; NO es una declaración de
# sequía (la oficial de CONAGUA combina lluvia, presas, ríos, vegetación, etc.). Por eso se
# reporta como "más seco de lo normal" y no como "sequía". El código D0-D4 queda como referencia.
CATEGORIAS_SEQUIA = [
    (2, "D4", "much drier than normal"),
    (5, "D3", "much drier than normal"),
    (10, "D2", "drier than normal"),
    (20, "D1", "drier than normal"),
    (30, "D0", "slightly drier than normal"),
]
MIN_MEDICIONES = 8  # por ventana de 30 días (SMAP pasa cada 2-3 días)


def categoria_sequia(percentil: float) -> tuple[str | None, str]:
    for limite, codigo, nombre in CATEGORIAS_SEQUIA:
        if percentil <= limite:
            return codigo, nombre
    return None, "normal or wetter than normal"


def _restar_anios(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year - n)
    except ValueError:  # 29 de febrero
        return d.replace(year=d.year - n, day=28)


async def estado_sequia(lat: float, lon: float, dias: int = 30) -> dict:
    """Promedio de humedad SMAP de los últimos `dias` días contra el MISMO periodo de cada año desde
    2015, clasificado con los percentiles del Drought Monitor (D0-D4)."""
    fin = date.today() - timedelta(days=1)  # SMAP tiene ~1 día de retraso
    inicio = fin - timedelta(days=dias - 1)
    anios = list(range(1, fin.year - PRIMER_ANIO + 1))
    rangos = [(inicio, fin)] + [(_restar_anios(inicio, n), _restar_anios(fin, n)) for n in anios]
    datos = await serie(lat, lon, rangos)

    def ventana(i: date, f: date) -> list[dict]:
        return [m for k in range((f - i).days + 1) if (m := datos.get((i + timedelta(days=k)).isoformat()))]

    actual = ventana(inicio, fin)
    if len(actual) < MIN_MEDICIONES:
        return {"categoria": None, "mensaje": f"SMAP has few recent measurements at this point ({len(actual)})"}

    historicos = []
    for n in anios:
        v = ventana(_restar_anios(inicio, n), _restar_anios(fin, n))
        if len(v) >= MIN_MEDICIONES:
            historicos.append(sum(m["humedad_pct_volumen"] for m in v) / len(v))
    if len(historicos) < 5:
        return {"categoria": None, "mensaje": "SMAP does not have enough years to compare at this point"}

    prom_actual = sum(m["humedad_pct_volumen"] for m in actual) / len(actual)
    promedio = sum(historicos) / len(historicos)
    percentil = round(100 * sum(1 for h in historicos if h < prom_actual) / len(historicos), 1)
    codigo, nombre = categoria_sequia(percentil)
    recomendadas = sum(1 for m in actual if m["calidad_recomendada"])

    return {
        "categoria": codigo,
        "estado": nombre,
        "periodo": {"inicio": inicio.isoformat(), "fin": fin.isoformat(), "dias": dias},
        "humedad_promedio": round(prom_actual, 1),
        "promedio_historico_periodo": round(promedio, 1),
        "diferencia_vs_promedio": round(prom_actual - promedio, 1),
        "percentil": percentil,
        "anios_comparados": len(historicos),
        "mediciones_periodo": len(actual),
        "pct_calidad_recomendada": round(100 * recomendadas / len(actual)),
        "metodo": (
            f"Average SMAP moisture over {dias} days vs. the same period of {len(historicos)} years "
            f"({PRIMER_ANIO} onward); Drought Monitor percentile cuts (D0 <=30, D1 <=20, D2 <=10, "
            "D3 <=5, D4 <=2). Measures only soil moisture: not an official drought declaration"
        ),
        "fuente": "NASA SMAP L3 Enhanced (SPL3SMP_E v006), 9 km",
        # True si la celda del punto no tiene datos (ciudad o agua) y se usó la vecina, a ~9 km
        "celda_vecina": (await celda_para(lat, lon))[2],
    }


# ---------- Humedad en la zona de raíces: SMAP L4 (SPL4SMGP) ----------
# L4 NO es medición pura: es el modelo de superficie de NASA al que se le "asimilan" (corrigen) las
# mediciones de SMAP. Da la humedad de 0-5 cm y de la zona de raíces (0-100 cm) cada 3 horas, en la
# misma cuadrícula de 9 km, con ~3-4 días de retraso. Se toma el archivo de 12:00-15:00 UTC de cada día.

COLECCION_L4 = "C3480440870-NSIDC_CPRD"  # SPL4SMGP v008
HORA_L4 = "T133000"


async def raiz(lat: float, lon: float, dias: int = 14) -> dict:
    fila, col, _ = await celda_para(lat, lon)
    hoy = date.today()
    v = f"[{fila - 1}:1:{fila + 1}][{col - 1}:1:{col + 1}]"
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cliente:
            granulos: dict[str, str] = {}
            pagina = 1
            while True:
                r = await cliente.get(CMR, params={
                    "collection_concept_id": COLECCION_L4,
                    "temporal": f"{(hoy - timedelta(days=dias)).isoformat()}T00:00:00Z,{hoy.isoformat()}T23:59:59Z",
                    "sort_key": "-start_date",
                    "page_size": 200,
                    "page_num": pagina,
                })
                r.raise_for_status()
                entradas = r.json()["feed"]["entry"]
                for g in entradas:
                    if HORA_L4 in g["title"]:
                        granulos.setdefault(g["time_start"][:10], g["title"])
                if len(entradas) < 200:
                    break
                pagina += 1

            semaforo = asyncio.Semaphore(CONSULTAS_SIMULTANEAS)

            async def una(fecha: str, granulo: str):
                async with semaforo:
                    resp = await cliente.get(
                        OPENDAP.format(c=COLECCION_L4, g=granulo),
                        params={"dap4.ce": f"/Geophysical_Data/sm_rootzone{v};/Geophysical_Data/sm_surface{v}"},
                        headers={"Authorization": f"Bearer {_token()}"},
                    )
                    resp.raise_for_status()
                    d = _leer_csv(resp.text)
                    valor_raiz, valor_sup = d["sm_rootzone"][1][1], d["sm_surface"][1][1]
                    if valor_raiz == SIN_DATO or valor_raiz < 0:
                        return None
                    return {
                        "fecha": fecha,
                        "raiz_pct_volumen": round(valor_raiz * 100, 1),
                        "superficie_pct_volumen": round(valor_sup * 100, 1) if valor_sup >= 0 else None,
                    }

            resultados = await asyncio.gather(*(una(f, g) for f, g in granulos.items()), return_exceptions=True)
    except httpx.HTTPError as e:
        raise RuntimeError("SMAP L4 (NASA Earthdata) did not respond. Please try again in a moment.") from e

    lista = sorted((x for x in resultados if isinstance(x, dict)), key=lambda x: x["fecha"])
    return {
        "ultima": lista[-1] if lista else None,
        "serie": lista,
        "nota": "Root zone = 0-100 cm. SMAP L4 is the NASA model corrected with SMAP measurements (not a direct measurement).",
        "fuente": "NASA SMAP L4 (SPL4SMGP v008), 9 km",
    }
