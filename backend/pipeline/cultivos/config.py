"""Rutas y parámetros de la pipeline de Cultivos.

Todas las decisiones ajustables (ventana de años, año base de precios, umbrales)
viven aquí para no buscarlas por el código.
"""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"

# ---- Entradas ----
SIAP_DIR = DATA_DIR / "siap"
SEQUIA_XLSX = DATA_DIR / "sequia" / "MunicipiosSequia.xlsx"
ECOCROP_CSV = DATA_DIR / "ecocrop" / "EcoCrop_DB.csv"
INFLACION_CSV = DATA_DIR / "inflacion" / "inflacion_mexico.csv"
CURADO_JSON = Path(__file__).resolve().parent / "curado.json"

# ---- Salida (lo que lee la API) ----
SALIDA_DIR = DATA_DIR / "cultivos"

# ---- URLs de descarga (ver descargas.py) ----
URL_SEQUIA = (
    "https://smn.conagua.gob.mx/tools/RESOURCES/"
    "Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx"
)
URL_ECOCROP = "https://raw.githubusercontent.com/OpenCLIM/ecocrop/main/EcoCrop_DB.csv"
# Inflación promedio anual (%), FMI World Economic Outlook. Equivale a la variación
# del INPC promedio anual; la API de INEGI pide token y esta no.
URL_INFLACION = "https://www.imf.org/external/datamapper/api/v1/PCPIPCH/MEX"

# ---- Parámetros ----
VENTANA_ANIOS = 10          # años hacia atrás para medianas y percentiles
ANIO_BASE_PRECIOS = 2025    # precios reales en pesos de este año
MIN_ANIOS_ESTADISTICA = 3   # con menos años no se calculan percentiles ni CV

# Una temporada cuenta como "con sequía severa" si al menos esta fracción de las
# lecturas del Monitor dentro de la temporada fue D2 o peor.
UMBRAL_LECTURAS_D2 = 0.25
# Para estado/nación: temporada con sequía si esta fracción de municipios la tuvo.
UMBRAL_MUNICIPIOS_SEQUIA = 0.30

# Meses de cada ciclo agrícola SIAP para cruzar con el Monitor de Sequía.
# (desfase de año, mes inicial) -> (desfase, mes final), relativos al año agrícola.
TEMPORADAS = {
    "OI": ((-1, 10), (0, 5)),   # octubre del año anterior a mayo
    "PV": ((0, 4), (0, 11)),    # abril a noviembre
    "PER": ((0, 1), (0, 12)),   # todo el año
}

CICLOS = {"Otoño-Invierno": "OI", "Primavera-Verano": "PV", "Perennes": "PER"}
# Los valores que salen en los JSON van en inglés (los datos de Cultivos se publican en inglés).
NOMBRE_CICLO = {"OI": "Fall-Winter", "PV": "Spring-Summer", "PER": "Perennial"}
MODALIDADES = {"Riego": "irrigated", "Temporal": "rainfed"}
