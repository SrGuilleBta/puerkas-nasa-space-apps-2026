import json
import os
import re
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

# Reemplazos parciales para descriptores o variedades compuestas
TERMINOS_COMPUESTOS = [
    (r"\bJITOMATE\b", "TOMATO"),
    (r"\bTOMATE VERDE\b", "TOMATILLO"),
    (r"\bTOMATE ROJO\b", "RED TOMATO"),
    (r"\bTOMATE\b", "TOMATO"),
    (r"\bAGUACATE\b", "AVOCADO"),
    (r"\bLIMON\b", "LIME"),
    (r"\bCEBOLLA\b", "ONION"),
    (r"\bCHILE\b", "CHILI PEPPER"),
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
    if os.path.exists(RUTA_CACHE_TRAD):
        try:
            with open(RUTA_CACHE_TRAD, "r", encoding="utf-8") as f:
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


print("1. Cargando datasets de histórico y predicciones...")
df_hist = pd.read_parquet("market_data/dataset_agricola_por_estado.parquet")
df_pred = pd.read_parquet("market_data/predicciones_agricolas_nacionales.parquet")

df_hist["fecha"] = pd.to_datetime(df_hist["fecha"])
columna_fecha_pred = "fecha_prediccion" if "fecha_prediccion" in df_pred.columns else "fecha"
df_pred[columna_fecha_pred] = pd.to_datetime(df_pred[columna_fecha_pred])

posibles_columnas_precio = ["precio_estimado", "yhat", "precio_por_kilo", "precio", "valor"]
columna_precio_pred = next((col for col in posibles_columnas_precio if col in df_pred.columns), None)

anio_actual = pd.Timestamp.now().year
df_hist_reciente = df_hist[df_hist["fecha"] >= f"{anio_actual}-01-01"].sort_values("fecha")

# 2. Traducir catálogo de productos únicos
cache_trad = cargar_cache()
traductor = GoogleTranslator(source="es", target="en") if TRADUCTOR_DISPONIBLE else None

productos_unicos = sorted(df_pred["producto"].unique())
print(f"2. Traduciendo {len(productos_unicos)} productos al inglés...")

mapa_productos_en = {
    prod: traducir_producto(prod, cache_trad, traductor)
    for prod in productos_unicos
}

os.makedirs("market_data", exist_ok=True)
with open(RUTA_CACHE_TRAD, "w", encoding="utf-8") as f:
    json.dump(cache_trad, f, ensure_ascii=False, indent=2)

# Mostrar resumen de traducciones en consola
print("\n   Muestra de traducciones aplicadas:")
for prod_es in productos_unicos[:15]:
    print(f"   - {prod_es:<22} -> {mapa_productos_en[prod_es]}")
if len(productos_unicos) > 15:
    print(f"   ... y {len(productos_unicos) - 15} más (guardados en '{RUTA_CACHE_TRAD}').\n")

# 3. Construir el JSON agrupando si dos variantes en español se tradujeron al mismo término en inglés
estructura_web = {}
estados = sorted(df_pred["estado"].unique())

for estado in estados:
    estado_en = traducir_estado(estado)
    if estado_en not in estructura_web:
        estructura_web[estado_en] = {}

    prods_estado = sorted(df_pred[df_pred["estado"] == estado]["producto"].unique())

    for prod in prods_estado:
        prod_en = mapa_productos_en.get(prod, prod)

        h = df_hist_reciente[(df_hist_reciente["estado"] == estado) & (df_hist_reciente["producto"] == prod)]
        p = df_pred[(df_pred["estado"] == estado) & (df_pred["producto"] == prod)]

        serie_combinada = {}

        for _, row in h.iterrows():
            f_str = row["fecha"].strftime("%Y-%m-%d")
            serie_combinada[f_str] = {
                "fecha": f_str,
                "real": round(float(row["precio_por_kilo"]), 2),
                "proyeccion": None,
            }

        if not h.empty and not p.empty:
            ultima_fecha = h.iloc[-1]["fecha"].strftime("%Y-%m-%d")
            ultimo_valor = round(float(h.iloc[-1]["precio_por_kilo"]), 2)
            if ultima_fecha in serie_combinada:
                serie_combinada[ultima_fecha]["proyeccion"] = ultimo_valor

        for _, row in p.iterrows():
            f_str = row[columna_fecha_pred].strftime("%Y-%m-%d")
            if f_str not in serie_combinada:
                serie_combinada[f_str] = {"fecha": f_str, "real": None}
            serie_combinada[f_str]["proyeccion"] = round(float(row[columna_precio_pred]), 2)

        lista_ordenada = sorted(serie_combinada.values(), key=lambda x: x["fecha"])
        estructura_web[estado_en][prod_en] = lista_ordenada

os.makedirs("market_front/src", exist_ok=True)
with open("market_front/src/datos_dashboard.json", "w", encoding="utf-8") as f:
    json.dump(estructura_web, f, ensure_ascii=False)

print("¡Listo! Archivo 'market_front/src/datos_dashboard.json' exportado en inglés.")