import json
import os
import re
import unicodedata
from pathlib import Path
import pandas as pd

try:
    from deep_translator import GoogleTranslator
    TRADUCTOR_DISPONIBLE = True
except ImportError:
    TRADUCTOR_DISPONIBLE = False

RUTA_CACHE_TRAD = "market_data/cache_traducciones.json"

# 1. Glosario canónico (adaptado a las llaves limpias sin acentos ni Ñ de tu Parquet)
GLOSARIO_EXACTO = {
    "AGUACATE": "AVOCADO",
    "AGUACATE HASS": "HASS AVOCADO",
    "AJO": "GARLIC",
    "ALCACHOFA": "ARTICHOKE",
    "APIO": "CELERY",
    "BETABEL": "BEETROOT",
    "BROCOLI": "BROCCOLI",
    "CALABACITA": "ZUCCHINI",
    "CEBOLLA": "ONION",
    "CEBOLLA BLANCA": "WHITE ONION",
    "CEBOLLA MORADA": "RED ONION",
    "CHAMPIÑON": "MUSHROOM",
    "CHAMPINON": "MUSHROOM",
    "CHAYOTE": "CHAYOTE SQUASH",
    "CHIA": "CHIA SEEDS",
    "CHICHARO": "GREEN PEAS",
    "CHILACA": "CHILACA PEPPER",
    "CHILE": "CHILI PEPPER",
    "CHILE HABANERO": "HABANERO PEPPER",
    "CHILE JALAPENO": "JALAPENO PEPPER",
    "CHILE POBLANO": "POBLANO PEPPER",
    "CHILE SERRANO": "SERRANO PEPPER",
    "CILANTRO": "CILANTRO",
    "CIRUELA": "PLUM",
    "COL": "CABBAGE",
    "COLIFLOR": "CAULIFLOWER",
    "DURAZNO": "PEACH",
    "EJOTE": "GREEN BEANS",
    "ELOTE": "CORN",
    "ESPARRAGO": "ASPARAGUS",
    "ESPINACA": "SPINACH",
    "FRESA": "STRAWBERRY",
    "FRIJOL": "BEANS",
    "FRIJOL NEGRO": "BLACK BEANS",
    "FRIJOL PINTO": "PINTO BEANS",
    "FRIJOL FLOR DE MAYO": "FLOR DE MAYO BEANS",
    "FRIJOL FLOR DE JUNIO": "FLOR DE JUNIO BEANS",
    "FRIJOL PERUANO": "PERUVIAN BEANS",
    "FRIJOL BAYO": "BAYO BEANS",
    "GARBANZO": "CHICKPEAS",
    "GUANABANA": "SOURSOP (GUANABANA)",
    "GUAYABA": "GUAVA",
    "HABA": "FAVA BEANS",
    "JALAPENO": "JALAPENO PEPPER",
    "JICAMA": "JICAMA",
    "JITOMATE": "TOMATO",
    "JITOMATE BOLA": "BEEFSTEAK TOMATO",
    "JITOMATE SALADETTE": "ROMA TOMATO (SALADETTE)",
    "LECHUGA": "LETTUCE",
    "LECHUGA ROMANA": "ROMAINE LETTUCE",
    "LENTEJA": "LENTILS",
    "LIMON": "LIME",
    "LIMON CON SEMILLA": "KEY LIME (WITH SEEDS)",
    "LIMON SIN SEMILLA": "PERSIAN LIME (SEEDLESS)",
    "MAIZ": "CORN",
    "MAIZ PALOMERO": "POPCORN MAIZE",
    "MAMEY": "MAMEY SAPOTE",
    "MANDARINA": "TANGERINE",
    "MANGO": "MANGO",
    "MANGO ATAULFO": "ATAULFO MANGO",
    "MANGO MANILA": "MANILA MANGO",
    "MANGO PARAISO": "PARAISO MANGO",
    "MANZANA": "APPLE",
    "MANZANA GOLDEN": "GOLDEN DELICIOUS APPLE",
    "MANZANA RED DELICIOUS": "RED DELICIOUS APPLE",
    "MANZANA GALA": "GALA APPLE",
    "MELON": "CANTALOUPE (MELON)",
    "MELON CHINO": "CANTALOUPE",
    "MELON VALENCIANO": "HONEYDEW MELON",
    "NARANJA": "ORANGE",
    "NOPAL": "PRICKLY PEAR CACTUS (NOPAL)",
    "PAPA": "POTATO",
    "PAPA ALPHA": "ALPHA POTATO",
    "PAPAYA": "PAPAYA",
    "PAPAYA MARADOL": "MARADOL PAPAYA",
    "PEPINO": "CUCUMBER",
    "PERA": "PEAR",
    "PERA DANJOU": "D'ANJOU PEAR",
    "PERA BOSC": "BOSC PEAR",
    "PEREJIL": "PARSLEY",
    "PERON": "GOLDEN APPLE (PERON)",
    "PINA": "PINEAPPLE",
    "PLATANO": "BANANA",
    "PLATANO MACHO": "PLANTAIN",
    "PLATANO TABASCO": "CAVENDISH BANANA",
    "PLATANO DOMINICO": "BABY BANANA (DOMINICO)",
    "RABANO": "RADISH",
    "REPOLLO": "CABBAGE",
    "SANDIA": "WATERMELON",
    "TOMATE": "TOMATILLO / TOMATO",
    "TOMATE ROJO": "RED TOMATO",
    "TOMATE VERDE": "TOMATILLO (HUSK TOMATO)",
    "TORONJA": "GRAPEFRUIT",
    "TUNA": "PRICKLY PEAR FRUIT",
    "UVA": "GRAPE",
    "UVA GLOBO": "RED GLOBE GRAPE",
    "UVA BLANCA": "GREEN GRAPE",
    "UVA ROJA": "RED GRAPE",
    "ZANAHORIA": "CARROT",
}

# Correcciones al glosario: traducciones que salían literales, sin traducir o con una palabra en español.
# "TOMATE" a secas es el tomate verde (tomatillo); el tomate rojo es "JITOMATE".
GLOSARIO_EXACTO.update({
    "ALUBIA": "WHITE BEANS (ALUBIA)",
    "AMARANTO": "AMARANTH",
    "CALABAZA": "SQUASH (CALABAZA)",
    "CHILE FRESCO": "FRESH CHILI PEPPER",
    "CHILE SECO": "DRIED CHILI PEPPER",
    "ELOTE": "SWEET CORN (ELOTE)",
    "GRANADA": "POMEGRANATE",
    "LINAZA": "FLAXSEED",
    "MELON": "CANTALOUPE",
    "PIMIENTO": "BELL PEPPER",
    "SEMILLA DE GIRASOL": "SUNFLOWER SEEDS",
    "SOYA": "SOYBEAN",
    "TOMATE": "TOMATILLO (GREEN TOMATO)",
    "VERDOLAGA": "PURSLANE (VERDOLAGA)",
})


# Reemplazos parciales para descriptores o variedades compuestas
TERMINOS_COMPUESTOS = [
    (r"\bJITOMATE\b", "TOMATO"),
    (r"\bTOMATE VERDE\b", "TOMATILLO"),
    (r"\bTOMATE ROJO\b", "RED TOMATO"),
    (r"\bTOMATE\b", "TOMATO"),
    (r"\bAGUACATE\b", "AVOCADO"),
    (r"\bLIMON\b", "LIME"),
    (r"\bCEBOLLA\b", "ONION"),
    (r"\bCHILE FRESCO\b", "FRESH CHILI PEPPER"),
    (r"\bCHILE SECO\b", "DRY CHILI PEPPER"),
    (r"\bSEMILLA DE GIRASOL\b", "SUNFLOWER SEED"),
    (r"\bJALAPENO\b", "JALAPENO"),
    (r"\bSERRANO\b", "SERRANO"),
    (r"\bPOBLANO\b", "POBLANO"),
    (r"\bHABANERO\b", "HABANERO"),
    (r"\bPAPA\b", "POTATO"),
    (r"\bZANAHORIA\b", "CARROT"),
    (r"\bCALABACITA\b", "ZUCCHINI"),
    (r"\bCHAYOTE\b", "CHAYOTE SQUASH"),
    (r"\bEJOTE\b", "GREEN BEANS"),
    (r"\bELOTE\b", "CORN"),
    (r"\bNOPAL\b", "NOPAL CACTUS"),
    (r"\bCHICHARO\b", "GREEN PEAS"),
    (r"\bCHAMPINON\b", "MUSHROOM"),
    (r"\bGUANABANA\b", "SOURSOP"),
    (r"\bBROCOLI\b", "BROCCOLI"),
    (r"\bCOLIFLOR\b", "CAULIFLOWER"),
    (r"\bESPINACA\b", "SPINACH"),
    (r"\bLECHUGA\b", "LETTUCE"),
    (r"\bPEPINO\b", "CUCUMBER"),
    (r"\bRABANO\b", "RADISH"),
    (r"\bBETABEL\b", "BEETROOT"),
    (r"\bAPIO\b", "CELERY"),
    (r"\bAJO\b", "GARLIC"),
    (r"\bFRIJOL\b", "BEANS"),
    (r"\bLENTEJA\b", "LENTILS"),
    (r"\bGARBANZO\b", "CHICKPEAS"),
    (r"\bHABA\b", "FAVA BEANS"),
    (r"\bMAIZ PALOMERO\b", "POPCORN MAIZE"),
    (r"\bMAIZ\b", "CORN"),
    (r"\bMANZANA\b", "APPLE"),
    (r"\bPERON\b", "GOLDEN APPLE (PERON)"),
    (r"\bPERA\b", "PEAR"),
    (r"\bPLATANO\b", "BANANA"),
    (r"\bNARANJA\b", "ORANGE"),
    (r"\bMANDARINA\b", "TANGERINE"),
    (r"\bTORONJA\b", "GRAPEFRUIT"),
    (r"\bDURAZNO\b", "PEACH"),
    (r"\bFRESA\b", "STRAWBERRY"),
    (r"\bSANDIA\b", "WATERMELON"),
    (r"\bMELON\b", "MELON"),
    (r"\bPINA\b", "PINEAPPLE"),
    (r"\bGUAYABA\b", "GUAVA"),
    (r"\bUVA\b", "GRAPE"),
    (r"\bCIRUELA\b", "PLUM"),
    (r"\bTUNA\b", "PRICKLY PEAR FRUIT"),
    (r"\bSIN SEMILLA\b", "SEEDLESS"),
    (r"\bCON SEMILLA\b", "WITH SEEDS"),
    (r"\bBLANCA\b", "WHITE"),
    (r"\bBLANCO\b", "WHITE"),
    (r"\bROJA\b", "RED"),
    (r"\bROJO\b", "RED"),
    (r"\bVERDE\b", "GREEN"),
    (r"\bNEGRO\b", "BLACK"),
    (r"\bMORADA\b", "RED/PURPLE"),
    (r"\bAMARILLA\b", "YELLOW"),
    (r"\bAMARILLO\b", "YELLOW"),
    (r"\bBOLA\b", "BEEFSTEAK"),
    (r"\bSALADETTE\b", "ROMA"),
    (r"\bGRANEL\b", "BULK"),
    (r"\bMALLA\b", "MESH BAG"),
    (r"\bPRIMERA\b", "GRADE A"),
]

# 2. Diccionario de Estados en inglés
ESTADOS_EN = {
    "AGUASCALIENTES": "AGUASCALIENTES",
    "BAJA CALIFORNIA": "BAJA CALIFORNIA",
    "BAJA CALIFORNIA SUR": "BAJA CALIFORNIA SUR",
    "CAMPECHE": "CAMPECHE",
    "CHIAPAS": "CHIAPAS",
    "CHIHUAHUA": "CHIHUAHUA",
    "CIUDAD DE MEXICO": "MEXICO CITY",
    "COAHUILA": "COAHUILA",
    "COLIMA": "COLIMA",
    "DURANGO": "DURANGO",
    "MEXICO": "STATE OF MEXICO",
    "ESTADO DE MEXICO": "STATE OF MEXICO",
    "GUANAJUATO": "GUANAJUATO",
    "GUERRERO": "GUERRERO",
    "HIDALGO": "HIDALGO",
    "JALISCO": "JALISCO",
    "MICHOACAN": "MICHOACAN",
    "MORELOS": "MORELOS",
    "NAYARIT": "NAYARIT",
    "NUEVO LEON": "NUEVO LEON",
    "OAXACA": "OAXACA",
    "PUEBLA": "PUEBLA",
    "QUERETARO": "QUERETARO",
    "QUINTANA ROO": "QUINTANA ROO",
    "SAN LUIS POTOSI": "SAN LUIS POTOSI",
    "SINALOA": "SINALOA",
    "SONORA": "SONORA",
    "TABASCO": "TABASCO",
    "TAMAULIPAS": "TAMAULIPAS",
    "TLAXCALA": "TLAXCALA",
    "VERACRUZ": "VERACRUZ",
    "YUCATAN": "YUCATAN",
    "ZACATECAS": "ZACATECAS",
}


def cargar_cache():
    ruta = Path(__file__).resolve().parent.parent / RUTA_CACHE_TRAD
    if ruta.exists():
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def traducir_producto(nombre_es, cache, traductor):
    clave = nombre_es.strip().upper()

    # 1. Prioridad máxima: Glosario exacto
    if clave in GLOSARIO_EXACTO:
        cache[clave] = GLOSARIO_EXACTO[clave]
        return GLOSARIO_EXACTO[clave]

    # 2. Caché guardado previamente
    if clave in cache:
        return cache[clave]

    # 3. Reemplazo por términos compuestos
    texto_trad = clave
    for patron, reemplazo in TERMINOS_COMPUESTOS:
        texto_trad = re.sub(patron, reemplazo, texto_trad, flags=re.IGNORECASE)

    # 4. Si no cambió nada y GoogleTranslator está disponible, consultar API
    if texto_trad == clave and TRADUCTOR_DISPONIBLE and traductor is not None:
        try:
            traduccion_api = traductor.translate(clave.lower()).upper()
            if traduccion_api:
                texto_trad = traduccion_api
        except Exception:
            pass

    texto_trad = re.sub(r"\s+", " ", texto_trad).strip()
    cache[clave] = texto_trad
    return texto_trad


def traducir_estado(estado_es):
    clave = estado_es.strip().upper()
    return ESTADOS_EN.get(clave, clave)


# Salida: archivos compactos por estado que lee el backend (backend/app/services/mercado.py).
#   backend/data/mercado/meta.json            estados, productos y fechas de corte
#   backend/data/mercado/estados/<estado>.json  precios reales y proyección de cada producto en ese estado
# Se puede correr desde cualquier carpeta:  python market_scripts/exportar_json.py
# (los datos de entrada se buscan junto a esta carpeta; la salida se puede cambiar con MERCADO_SALIDA)
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_SALIDA = Path(os.environ.get("MERCADO_SALIDA") or RAIZ / "backend" / "data" / "mercado")
DIAS_HISTORIAL = 400  # un poco más de un año de precios reales: alcanza para el rango "1 año"
DIAS_REALES_DIARIOS = 90  # lo anterior se guarda como promedio semanal: pesa menos y la gráfica de 1 año se ve igual
DIAS_PROYECCION_DIARIOS = 30  # la proyección lejana se guarda cada 7 días


def slug(texto):
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_")


def real_compacto(fechas, precios):
    """Precios reales: diarios los últimos DIAS_REALES_DIARIOS días y, antes, el promedio de cada semana."""
    pares = list(zip(fechas, precios))
    if not pares:
        return []
    corte = pares[-1][0] - pd.Timedelta(days=DIAS_REALES_DIARIOS)
    semanas = {}
    for f, v in pares:
        if f < corte:
            semanas.setdefault(f.isocalendar()[:2], []).append((f, float(v)))
    semanal = [[g[-1][0].strftime("%Y-%m-%d"), round(sum(v for _, v in g) / len(g), 2)] for _, g in sorted(semanas.items())]
    diario = [[f.strftime("%Y-%m-%d"), round(float(v), 2)] for f, v in pares if f >= corte]
    return semanal + diario


def proyeccion_compacta(fechas, precios):
    """Proyección: diaria los primeros DIAS_PROYECCION_DIARIOS días y después un punto por semana (y el último)."""
    pares = list(zip(fechas, precios))
    return [
        [f.strftime("%Y-%m-%d"), round(float(v), 2)]
        for i, (f, v) in enumerate(pares)
        if i < DIAS_PROYECCION_DIARIOS or i % 7 == 0 or i == len(pares) - 1
    ]


print("1. Cargando datasets de histórico y predicciones...")
df_hist = pd.read_parquet(RAIZ / "market_data" / "dataset_agricola_por_estado.parquet")
df_pred = pd.read_parquet(RAIZ / "market_data" / "predicciones_agricolas_nacionales.parquet")

df_hist["fecha"] = pd.to_datetime(df_hist["fecha"])
columna_fecha_pred = "fecha_prediccion" if "fecha_prediccion" in df_pred.columns else "fecha"
df_pred[columna_fecha_pred] = pd.to_datetime(df_pred[columna_fecha_pred])

posibles_columnas_precio = ["precio_estimado", "yhat", "precio_por_kilo", "precio", "valor"]
columna_precio_pred = next((col for col in posibles_columnas_precio if col in df_pred.columns), None)

ultimo_real_global = df_hist["fecha"].max()
df_hist_reciente = df_hist[df_hist["fecha"] >= ultimo_real_global - pd.Timedelta(days=DIAS_HISTORIAL)]
# Un precio por día (hay varias tiendas por día y estado)
df_hist_reciente = (
    df_hist_reciente.groupby(["estado", "producto", "fecha"], as_index=False)["precio_por_kilo"].mean()
)

# 2. Traducir catálogo de productos únicos
cache_trad = cargar_cache()
traductor = GoogleTranslator(source="es", target="en") if TRADUCTOR_DISPONIBLE else None

productos_unicos = sorted(set(df_pred["producto"].unique()) | set(df_hist["producto"].unique()))
print(f"2. Traduciendo {len(productos_unicos)} productos al inglés...")

mapa_productos_en = {
    prod: traducir_producto(prod, cache_trad, traductor)
    for prod in productos_unicos
}

try:  # la caché de traducciones solo se actualiza si la carpeta se puede escribir
    os.makedirs(RAIZ / "market_data", exist_ok=True)
    with open(RAIZ / RUTA_CACHE_TRAD, "w", encoding="utf-8") as f:
        json.dump(cache_trad, f, ensure_ascii=False, indent=2)
except OSError:
    pass

print("\n   Muestra de traducciones aplicadas:")
for prod_es in productos_unicos[:15]:
    print(f"   - {prod_es:<22} -> {mapa_productos_en[prod_es]}")
if len(productos_unicos) > 15:
    print(f"   ... y {len(productos_unicos) - 15} más (guardados en '{RUTA_CACHE_TRAD}').\n")

# 3. Un archivo por estado: {producto en español: {nombre en inglés, real: [[fecha, precio]], proyeccion: [[fecha, precio]]}}
(CARPETA_SALIDA / "estados").mkdir(parents=True, exist_ok=True)
for viejo in (CARPETA_SALIDA / "estados").glob("*.json"):
    viejo.unlink()  # no dejar estados que ya no existen

meta_estados = []
estados = sorted(set(df_pred["estado"].unique()) | set(df_hist_reciente["estado"].unique()))
for estado in estados:
    productos_estado = {}
    h_estado = df_hist_reciente[df_hist_reciente["estado"] == estado]
    p_estado = df_pred[df_pred["estado"] == estado]
    for prod in sorted(set(h_estado["producto"].unique()) | set(p_estado["producto"].unique())):
        h = h_estado[h_estado["producto"] == prod].sort_values("fecha")
        p = p_estado[p_estado["producto"] == prod].sort_values(columna_fecha_pred)
        productos_estado[prod] = {
            "nombre": mapa_productos_en.get(prod, prod),
            "real": real_compacto(h["fecha"], h["precio_por_kilo"]),
            "proyeccion": proyeccion_compacta(p[columna_fecha_pred], p[columna_precio_pred]),
        }

    clave = slug(estado)
    with open(CARPETA_SALIDA / "estados" / f"{clave}.json", "w", encoding="utf-8") as f:
        json.dump(
            {"estado": estado, "estadoEn": traducir_estado(estado), "productos": productos_estado},
            f, ensure_ascii=False, separators=(",", ":"),
        )
    meta_estados.append({"clave": clave, "nombre": estado, "nombreEn": traducir_estado(estado), "productos": len(productos_estado)})

with open(CARPETA_SALIDA / "meta.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "ultimoDatoReal": ultimo_real_global.strftime("%Y-%m-%d"),
            "proyeccionHasta": df_pred[columna_fecha_pred].max().strftime("%Y-%m-%d"),
            "fuente": "Profeco, programa Quién es Quién en los Precios (precios al consumidor, por kilo)",
            "estados": meta_estados,
            "productos": {prod: mapa_productos_en.get(prod, prod) for prod in productos_unicos},
        },
        f, ensure_ascii=False, indent=1,
    )

print(f"¡Listo! {len(meta_estados)} estados exportados en '{CARPETA_SALIDA}'.")
