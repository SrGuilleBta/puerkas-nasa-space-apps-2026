import os
import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

# ==========================================
# 1. CONFIGURATION, CREDENTIALS & HTTP SESSION
# ==========================================
EPPO_API_KEY = os.getenv("EPPO_API_KEY", "575975242e06415e9d70269f24c4df10")
EPPO_BASE_URL = "https://api.eppo.int/gd/v2"
EPPO_HEADERS = {
    "X-Api-Key": EPPO_API_KEY,
    "Accept": "application/json"
}

METEO_USER = os.getenv("METEO_USER", "hackathon_nasa_space_apps_esquivel_eder")
METEO_PASS = os.getenv("METEO_PASS", "52aV0CsnXHf4GwfRj3Lc")
METEO_BASE_URL = "https://api.meteomatics.com"

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_PLAGAS_MX = os.path.join(DIRECTORIO_ACTUAL, "plagas-MX.json")

# English translation of EPPO status codes present in plagas-MX.json
MAPA_PESTSTATUS_EPPO = {
    "A": "Present (widespread)",
    "B": "Present (restricted distribution)",
    "C": "Present (few occurrences)",
    "X": "Present (no details)",
    "T": "Transient",
    "G": "Present (under control / greenhouse)",
    "H": "Present (historical / doubtful record)",
    "J": "Present (interception / uncertain status)",
    "K": "Present (under review)",
    "D": "Absent",
    "E": "Eradicated"
}


def crear_sesion_http() -> requests.Session:
    """
    Creates a reusable HTTP session (Keep-Alive) with a thread-safe connection pool
    and automatic retries for rate limits (HTTP 429) or transient 5xx errors.
    """
    sesion = requests.Session()
    estrategia_reintento = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adaptador = HTTPAdapter(
        pool_connections=32,
        pool_maxsize=32,
        max_retries=estrategia_reintento
    )
    sesion.mount("https://", adaptador)
    sesion.mount("http://", adaptador)
    return sesion


HTTP_SESSION = crear_sesion_http()
CACHE_LOCK = threading.Lock()


# ==========================================
# 2. EPPO API & LOCAL FILE FUNCTIONS
# ==========================================
def get_eppo(endpoint_path: str):
    """GET request to https://api.eppo.int/gd/v2/... reusing TCP connections."""
    url = f"{EPPO_BASE_URL}/{endpoint_path.lstrip('/')}"
    resp = HTTP_SESSION.get(url, headers=EPPO_HEADERS, timeout=20)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def extraer_diccionarios(data) -> list[dict]:
    """Extracts lists of objects regardless of nesting level in EPPO JSON responses."""
    resultado = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                resultado.append(item)
            elif isinstance(item, list):
                resultado.extend(extraer_diccionarios(item))
    elif isinstance(data, dict):
        if any(k in data for k in ("eppocode", "code", "fullname", "isolang", "url", "country", "isocode")):
            resultado.append(data)
        for valor in data.values():
            if isinstance(valor, (list, dict)):
                resultado.extend(extraer_diccionarios(valor))
    return resultado


def obtener_info_cultivo(cultivo_a_revisar: dict | str) -> dict:
    """
    Extracts crop metadata from the input JSON object and fetches the English
    common name from EPPO if not already provided.
    """
    if isinstance(cultivo_a_revisar, str):
        cultivo_obj = {"eppocode": cultivo_a_revisar.strip().upper()}
    elif isinstance(cultivo_a_revisar, dict):
        cultivo_obj = cultivo_a_revisar
    else:
        raise ValueError("cultivo_a_revisar must be a JSON dict or an eppocode string.")

    eppo_cultivo = str(cultivo_obj.get("eppocode") or "").strip().upper()
    if not eppo_cultivo:
        raise ValueError(f"Crop object does not contain a valid 'eppocode': {cultivo_obj}")

    nombre_es = cultivo_obj.get("nombre")
    nombre_en = cultivo_obj.get("nombre_en")
    nombre_cientifico = cultivo_obj.get("cientifico")

    # Query EPPO names if English name, Spanish name, or scientific name is missing
    if not nombre_en or not nombre_es or not nombre_cientifico:
        try:
            nombres_raw = get_eppo(f"taxons/taxon/{eppo_cultivo}/names")
            registros = extraer_diccionarios(nombres_raw)
            for n in registros:
                idioma = str(n.get("isolang") or n.get("lang") or "").lower()
                nom = n.get("fullname") or n.get("name")
                if not nom:
                    continue
                if idioma in ("la", "") and not nombre_cientifico:
                    nombre_cientifico = nom
                elif idioma.startswith("en") and not nombre_en:
                    nombre_en = nom
                elif idioma.startswith("es") and not nombre_es:
                    nombre_es = nom
            if not nombre_cientifico and registros:
                nombre_cientifico = registros[0].get("fullname") or eppo_cultivo
        except Exception:
            pass

    nombre_cientifico = nombre_cientifico or eppo_cultivo
    nombre_en = nombre_en or nombre_es or nombre_cientifico
    nombre_es = nombre_es or nombre_en

    return {
        "id": cultivo_obj.get("id", eppo_cultivo.lower()),
        "eppocode": eppo_cultivo,
        "common_name_en": nombre_en,
        "common_name_es": nombre_es,
        "scientific_name": nombre_cientifico,
        "family": cultivo_obj.get("familia"),
        "type": cultivo_obj.get("tipo"),
        "unit": cultivo_obj.get("unidad"),
        "practiced_cycles": cultivo_obj.get("ciclos_practicados", []),
        "cycle_days": cultivo_obj.get("ciclo_dias", []),
        "optimal_temperature_c": cultivo_obj.get("temperatura_optima_c", []),
        "absolute_temperature_c": cultivo_obj.get("temperatura_absoluta_c", []),
        "water": cultivo_obj.get("agua", {}),
        "care_guidelines": cultivo_obj.get("cuidados", []),
        "raw_crop_data": cultivo_obj
    }


def cargar_plagas_locales(ruta_archivo: str = RUTA_PLAGAS_MX) -> dict[str, dict]:
    """
    Loads the national pest catalog directly from the local plagas-MX.json file.
    """
    print(f"1. Loading national pest catalog from local file: {ruta_archivo}...")

    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"Pest file not found at: {ruta_archivo}")

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        datos_presencia = json.load(f)

    catalogo_pais = {}
    for reg in datos_presencia:
        if not isinstance(reg, dict):
            continue

        codigo = str(reg.get("eppocode") or "").strip().upper()
        if not codigo:
            continue

        pest_status = str(reg.get("peststatus") or "X").strip().upper()
        yr_erad = reg.get("yr_erad")

        # Exclude Absent (D) or Eradicated (E) pests
        if pest_status in ("D", "E") or yr_erad is not None:
            continue

        descripcion_estado = MAPA_PESTSTATUS_EPPO.get(pest_status, f"Present ({pest_status})")
        yr_sit = reg.get("yr_situation")
        if yr_sit:
            descripcion_estado = f"{descripcion_estado} - Situation {yr_sit}"

        catalogo_pais[codigo] = {
            "eppocode": codigo,
            "prefname": reg.get("prefname"),
            "peststatus": pest_status,
            "country_status": descripcion_estado,
            "eppo_country_data": reg
        }

    print(f"   ✔ Local file loaded: {len(catalogo_pais)} active pests registered.")
    return catalogo_pais


def obtener_expediente_completo_plaga(eppo_plaga: str, info_base: dict, info_pais: dict) -> dict:
    """Queries all 8 EPPO v2 Taxon endpoints in parallel to build the pest dossier in English."""
    endpoints = {
        "kingdom": f"taxons/taxon/{eppo_plaga}/kingdom",
        "taxonomy": f"taxons/taxon/{eppo_plaga}/taxonomy",
        "names": f"taxons/taxon/{eppo_plaga}/names",
        "hosts": f"taxons/taxon/{eppo_plaga}/hosts",
        "vectors": f"taxons/taxon/{eppo_plaga}/vectors",
        "bcas": f"taxons/taxon/{eppo_plaga}/bcas",
        "categorization": f"taxons/taxon/{eppo_plaga}/categorization",
        "photos": f"taxons/taxon/{eppo_plaga}/photos",
    }

    respuestas = {}

    def consultar_eppo_seguro(clave: str, ruta: str):
        try:
            return clave, get_eppo(ruta)
        except Exception:
            return clave, None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = [executor.submit(consultar_eppo_seguro, k, v) for k, v in endpoints.items()]
        for futuro in as_completed(futuros):
            clave, data = futuro.result()
            respuestas[clave] = data

    # 1. Kingdom and taxonomy
    tipo_biologico = "FUNGUS"
    familia_taxonomica = "Not specified"
    texto_reino = str(respuestas.get("kingdom") or "").lower()
    if any(k in texto_reino for k in ["animalia", "insecta", "arthropoda", "acari", "nematoda"]):
        tipo_biologico = "INSECT"
    elif any(k in texto_reino for k in ["fungi", "chromista", "oomycota"]):
        tipo_biologico = "FUNGUS"
    elif any(k in texto_reino for k in ["bacteria", "virus", "viroid", "phytoplasma"]):
        tipo_biologico = "VECTOR_PATHOGEN"

    for t in extraer_diccionarios(respuestas.get("taxonomy")):
        nivel = str(t.get("rank") or t.get("level") or "").lower()
        if "famil" in nivel or "order" in nivel:
            familia_taxonomica = t.get("fullname") or t.get("prefname") or familia_taxonomica

    # 2. Scientific and common names (prioritizing English)
    nombre_cientifico = (
        info_base.get("fullname")
        or info_base.get("prefname")
        or info_pais.get("prefname")
        or eppo_plaga
    )
    nombres_es = []
    nombres_en = []
    for n in extraer_diccionarios(respuestas.get("names")):
        idioma = str(n.get("isolang") or n.get("lang") or "").lower()
        nom = n.get("fullname") or n.get("name")
        if not nom:
            continue
        if idioma.startswith("en") and nom not in nombres_en:
            nombres_en.append(nom)
        elif idioma.startswith("es") and nom not in nombres_es:
            nombres_es.append(nom)

    # 3. Host crops
    cultivos_afectados = []
    for h in extraer_diccionarios(respuestas.get("hosts")):
        nom_host = h.get("fullname") or h.get("prefname")
        cod_host = h.get("eppocode")
        if nom_host and len(cultivos_afectados) < 6:
            item_str = f"{nom_host} ({cod_host})" if cod_host else nom_host
            if item_str not in cultivos_afectados:
                cultivos_afectados.append(item_str)

    # 4. Transmission vectors
    vectores = []
    for v in extraer_diccionarios(respuestas.get("vectors"))[:4]:
        nom_vec = v.get("fullname") or v.get("prefname") or v.get("eppocode")
        if nom_vec and nom_vec not in vectores:
            vectores.append(nom_vec)

    # 5. Biological control agents (BCAs)
    control_biologico = []
    for b in extraer_diccionarios(respuestas.get("bcas"))[:5]:
        nom_bca = b.get("fullname") or b.get("prefname") or b.get("eppocode")
        if nom_bca and nom_bca not in control_biologico:
            control_biologico.append(nom_bca)

    # 6. Quarantine status
    estatus_cuarentena = []
    for c in extraer_diccionarios(respuestas.get("categorization"))[:4]:
        lista_q = c.get("qlist") or c.get("list") or c.get("status")
        pais_q = c.get("country") or c.get("isocode") or c.get("rppo") or ""
        if lista_q:
            estatus_cuarentena.append(f"{pais_q}: {lista_q}".strip(": "))

    # 7. Photos
    fotos_urls = []
    for p in extraer_diccionarios(respuestas.get("photos"))[:3]:
        url_foto = p.get("url") or p.get("file") or p.get("thumb") or p.get("original")
        if url_foto and url_foto not in fotos_urls:
            fotos_urls.append(url_foto)

    return {
        "eppocode": eppo_plaga,
        "scientific_name": nombre_cientifico,
        "common_name_en": nombres_en[0] if nombres_en else nombre_cientifico,
        "other_names_en": nombres_en[1:4],
        "common_name_es": nombres_es[0] if nombres_es else None,
        "biological_type": tipo_biologico,
        "reference_taxonomy": familia_taxonomica,
        "country_status": info_pais.get("country_status", "Present"),
        "quarantine_alerts": estatus_cuarentena,
        "host_crops_avoid_rotation": cultivos_afectados,
        "transmission_vectors": vectores,
        "recommended_biological_control": control_biologico,
        "photos": fotos_urls
    }


# ==========================================
# 3. METEOMATICS: 10-DAY TIME SERIES
# ==========================================
def obtener_clima_meteomatics(lat: float, lon: float) -> list[dict]:
    url = (
        f"{METEO_BASE_URL}/today-3DT00:00:00Z--today+6DT00:00:00Z:P1D/"
        f"t_max_2m_24h:C,t_min_2m_24h:C,relative_humidity_2m:p,prob_precip_24h:p/"
        f"{lat},{lon}/json"
    )
    print("2. Querying weather window (3 past days + 6 forecast days) in Meteomatics...")
    resp = HTTP_SESSION.get(url, auth=HTTPBasicAuth(METEO_USER, METEO_PASS), timeout=20)
    resp.raise_for_status()
    datos = resp.json()

    dias = {}
    for param in datos.get("data", []):
        p_name = param["parameter"]
        for d in param["coordinates"][0]["dates"]:
            fecha = d["date"][:10]
            dias.setdefault(fecha, {"date": fecha})
            if p_name == "t_max_2m_24h:C":
                dias[fecha]["t_max"] = d["value"]
            elif p_name == "t_min_2m_24h:C":
                dias[fecha]["t_min"] = d["value"]
            elif p_name == "relative_humidity_2m:p":
                dias[fecha]["humidity"] = d["value"]
            elif p_name == "prob_precip_24h:p":
                dias[fecha]["rain_prob"] = d["value"]

    for f in dias:
        dias[f]["t_avg"] = round((dias[f].get("t_max", 0) + dias[f].get("t_min", 0)) / 2.0, 1)

    return [dias[f] for f in sorted(dias.keys())]


# ==========================================
# 4. PARALLEL GEOSPATIAL RADAR (GBIF + iNaturalist)
# ==========================================
def limpiar_nombre_cientifico(nombre_eppo: str) -> str:
    partes = nombre_eppo.strip().replace("'", "").split()
    if len(partes) >= 2:
        if partes[0].lower() == "candidatus" and len(partes) >= 3:
            return f"{partes[1]} {partes[2]}"
        return f"{partes[0]} {partes[1]}"
    return nombre_eppo.strip()


def calcular_distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radio_tierra_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radio_tierra_km * c, 1)


def verificar_presencia_cercana_gps(nombre_cientifico: str, lat: float, lon: float, radio_km: float = 100.0) -> dict:
    especie = limpiar_nombre_cientifico(nombre_cientifico)

    delta_lat = radio_km / 111.0
    delta_lon = radio_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    lat_min, lat_max = round(lat - delta_lat, 4), round(lat + delta_lat, 4)
    lon_min, lon_max = round(lon - delta_lon, 4), round(lon + delta_lon, 4)

    def consultar_gbif() -> list[dict]:
        hallazgos = []
        try:
            gbif_url = "https://api.gbif.org/v1/occurrence/search"
            gbif_params = {
                "scientificName": especie,
                "decimalLatitude": f"{lat_min},{lat_max}",
                "decimalLongitude": f"{lon_min},{lon_max}",
                "hasCoordinate": "true",
                "limit": 30
            }
            resp_gbif = HTTP_SESSION.get(gbif_url, params=gbif_params, timeout=12)
            if resp_gbif.status_code == 200:
                for reg in resp_gbif.json().get("results", []):
                    r_lat = reg.get("decimalLatitude")
                    r_lon = reg.get("decimalLongitude")
                    if r_lat is not None and r_lon is not None:
                        dist = calcular_distancia_km(lat, lon, r_lat, r_lon)
                        if dist <= radio_km:
                            hallazgos.append({
                                "source": "GBIF",
                                "distance_km": dist,
                                "state_province": reg.get("stateProvince") or reg.get("locality") or "Nearby region",
                                "date": str(reg.get("eventDate") or reg.get("year") or "Historical")[:10],
                                "coordinates": [r_lat, r_lon]
                            })
        except Exception:
            pass
        return hallazgos

    def consultar_inat() -> list[dict]:
        hallazgos = []
        try:
            inat_url = "https://api.inaturalist.org/v1/observations"
            inat_params = {
                "taxon_name": especie,
                "lat": lat,
                "lng": lon,
                "radius": radio_km,
                "per_page": 20
            }
            resp_inat = HTTP_SESSION.get(inat_url, params=inat_params, timeout=12)
            if resp_inat.status_code == 200:
                for obs in resp_inat.json().get("results", []):
                    geojson = obs.get("geojson") or {}
                    coords = geojson.get("coordinates")
                    if coords and len(coords) == 2:
                        o_lon, o_lat = float(coords[0]), float(coords[1])
                        dist = calcular_distancia_km(lat, lon, o_lat, o_lon)
                        if dist <= radio_km:
                            hallazgos.append({
                                "source": "Naturalista/iNat",
                                "distance_km": dist,
                                "state_province": obs.get("place_guess") or "Nearby region",
                                "date": str(obs.get("observed_on") or "Recent")[:10],
                                "coordinates": [o_lat, o_lon]
                            })
        except Exception:
            pass
        return hallazgos

    avistamientos_cercanos = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_gbif = executor.submit(consultar_gbif)
        futuro_inat = executor.submit(consultar_inat)
        avistamientos_cercanos.extend(futuro_gbif.result())
        avistamientos_cercanos.extend(futuro_inat.result())

    avistamientos_cercanos.sort(key=lambda x: x["distance_km"])

    if avistamientos_cercanos:
        mas_cercano = avistamientos_cercanos[0]
        return {
            "detected_within_nearby_radius": True,
            "search_radius_km": radio_km,
            "total_records_in_zone": len(avistamientos_cercanos),
            "nearest_sighting_distance_km": mas_cercano["distance_km"],
            "nearest_location": mas_cercano["state_province"],
            "last_record_date": mas_cercano["date"],
            "sightings_sample": avistamientos_cercanos[:3]
        }
    else:
        return {
            "detected_within_nearby_radius": False,
            "search_radius_km": radio_km,
            "total_records_in_zone": 0,
            "nearest_sighting_distance_km": None,
            "nearest_location": f"No georeferenced reports within {radio_km} km",
            "last_record_date": None,
            "sightings_sample": []
        }


# ==========================================
# 5. SINGLE PEST EVALUATOR (THREAD-SAFE CACHE)
# ==========================================
def evaluar_plaga_individual(
    cod: str,
    info_base: dict,
    info_pais: dict,
    serie_clima: list[dict],
    lat: float,
    lon: float,
    cache_plagas: dict
) -> dict:
    with CACHE_LOCK:
        if cod in cache_plagas:
            print(f"      ⚡ {cod} retrieved from in-memory cache (shared pest across crops).")
            return cache_plagas[cod]

    expediente = obtener_expediente_completo_plaga(cod, info_base, info_pais)
    tipo = expediente["biological_type"]

    presencia_local = verificar_presencia_cercana_gps(
        expediente["scientific_name"], lat, lon, radio_km=100.0
    )
    expediente["nearby_geographic_presence"] = presencia_local

    racha = 0
    max_racha = 0
    gdd_total = 0.0
    dias_favorables_detalle = []

    for dia in serie_clima:
        t_max, t_min, t_med = dia["t_max"], dia["t_min"], dia["t_avg"]
        hum, lluvia = dia["humidity"], dia["rain_prob"]

        if tipo in ("INSECT", "VECTOR_PATHOGEN"):
            gdd_dia = max(0.0, t_med - 10.0)
            gdd_total += gdd_dia
            condicion = (18.0 <= t_max <= 35.0) and (hum >= 40.0)
            motivo = f"Useful heat (+{round(gdd_dia, 1)} GDD) and {t_max}°C"
        else:
            condicion = (12.0 <= t_med <= 26.0) and (hum >= 80.0 or lluvia >= 50.0)
            motivo = f"High humidity ({hum}%) / Rain prob ({lluvia}%)"

        if condicion:
            racha += 1
            max_racha = max(max_racha, racha)
            dias_favorables_detalle.append({"date": dia["date"], "condition": motivo})
        else:
            racha = 0

    if (tipo in ("INSECT", "VECTOR_PATHOGEN") and gdd_total >= 65.0) or (tipo == "FUNGUS" and max_racha >= 3):
        if presencia_local["detected_within_nearby_radius"]:
            riesgo = "CRITICAL"
            detalle_riesgo = "Favorable weather + Pest confirmed within 100 km of your coordinates"
            accion = (
                "Imminent outbreak risk confirmed in your region. Start field monitoring, "
                "release suggested biological control agents, and avoid rotating with listed host crops."
            )
        else:
            riesgo = "HIGH"
            detalle_riesgo = "Favorable weather for incubation, but no recent sightings within 100 km"
            accion = (
                "Weather favors incubation although there are no recent nearby reports. "
                "Maintain preventive surveillance and inspect host crops."
            )
    elif (tipo in ("INSECT", "VECTOR_PATHOGEN") and gdd_total >= 45.0) or (tipo == "FUNGUS" and max_racha == 2):
        riesgo = "MEDIUM"
        detalle_riesgo = "Partially favorable weather conditions"
        accion = "Monitor the underside of leaves and pheromone traps during critical days."
    else:
        riesgo = "LOW"
        detalle_riesgo = "Weather outside incubation threshold"
        accion = "Current weather conditions are outside the optimal threshold for mass incubation."

    expediente["climatic_evaluation"] = {
        "risk_level": riesgo,
        "geographic_climatic_diagnosis": detalle_riesgo,
        "max_consecutive_favorable_days": max_racha,
        "growing_degree_days_GDD": round(gdd_total, 1),
        "critical_days_detected": dias_favorables_detalle,
        "agronomic_recommendation": accion
    }

    with CACHE_LOCK:
        cache_plagas[cod] = expediente
    return expediente


# ==========================================
# 6. CROP PROCESSOR (CONCURRENT PEST EVALUATION)
# ==========================================
def procesar_cultivo_individual(
    cultivo_a_revisar: dict,
    catalogo_pais: dict[str, dict],
    serie_clima: list[dict],
    lat: float,
    lon: float,
    limite_plagas_por_cultivo: int | None,
    cache_plagas_evaluadas: dict,
    iso_pais: str = "MX",
    max_workers_plagas: int = 4
) -> tuple[dict, dict]:
    """
    Processes a single crop JSON object, cross-references its EPPO pests against
    the local plagas-MX.json file, and evaluates matching pests in parallel.
    """
    orden_prioridad = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}

    info_cultivo = obtener_info_cultivo(cultivo_a_revisar)
    eppo_cultivo = info_cultivo["eppocode"]

    plagas_cultivo_raw = get_eppo(f"taxons/taxon/{eppo_cultivo}/pests")
    lista_plagas_cultivo = extraer_diccionarios(plagas_cultivo_raw)

    plagas_coincidentes = []
    codigos_vistos = set()

    for p in lista_plagas_cultivo:
        cod = str(p.get("eppocode") or "").strip().upper()
        if not cod or cod in codigos_vistos:
            continue

        if cod in catalogo_pais:
            codigos_vistos.add(cod)
            plagas_coincidentes.append((cod, p, catalogo_pais[cod]))

    print(
        f"   -> {len(plagas_coincidentes)} pests of {info_cultivo['common_name_en']} "
        f"({eppo_cultivo}) present in {iso_pais} according to local catalog."
    )

    seleccion = plagas_coincidentes[:limite_plagas_por_cultivo]
    analisis_plagas_cultivo = []

    if seleccion:
        print(f"Evaluating {len(seleccion)} pests in parallel (workers={max_workers_plagas})...")
        with ThreadPoolExecutor(max_workers=max_workers_plagas) as executor:
            futuros_plagas = {
                executor.submit(
                    evaluar_plaga_individual,
                    cod, info_base, info_pais, serie_clima, lat, lon, cache_plagas_evaluadas
                ): cod
                for cod, info_base, info_pais in seleccion
            }

            for idx_p, futuro in enumerate(as_completed(futuros_plagas), start=1):
                cod_plaga = futuros_plagas[futuro]
                try:
                    expediente = futuro.result()
                    analisis_plagas_cultivo.append(expediente)
                    print(
                        f"   ✔ [{idx_p}/{len(seleccion)}] Pest {cod_plaga} processed "
                        f"for {info_cultivo['common_name_en']}."
                    )
                except Exception as exc:
                    print(f"   ✖ [{idx_p}/{len(seleccion)}] Error evaluating pest {cod_plaga}: {exc}")

    analisis_plagas_cultivo.sort(
        key=lambda x: (
            orden_prioridad.get(x["climatic_evaluation"]["risk_level"], 5),
            x["eppocode"]
        )
    )

    conteo_critico = sum(1 for p in analisis_plagas_cultivo if p["climatic_evaluation"]["risk_level"] == "CRITICAL")
    conteo_alto = sum(1 for p in analisis_plagas_cultivo if p["climatic_evaluation"]["risk_level"] == "HIGH")
    conteo_medio = sum(1 for p in analisis_plagas_cultivo if p["climatic_evaluation"]["risk_level"] == "MEDIUM")
    conteo_bajo = sum(1 for p in analisis_plagas_cultivo if p["climatic_evaluation"]["risk_level"] == "LOW")

    puntaje_riesgo = (conteo_critico * 10) + (conteo_alto * 5) + (conteo_medio * 2)

    if conteo_critico > 0:
        viabilidad = "NOT RECOMMENDED (Critical risk of active pests in the area)"
    elif conteo_alto > 0:
        viabilidad = "CAUTION (Requires preventive pest management)"
    else:
        viabilidad = "OPTIMAL FOR PLANTING / ROTATION (Low current phytosanitary risk)"

    resumen_cultivo = {
        "crop_id": info_cultivo["id"],
        "crop_eppocode": eppo_cultivo,
        "common_name_en": info_cultivo["common_name_en"],
        "common_name_es": info_cultivo["common_name_es"],
        "scientific_name": info_cultivo["scientific_name"],
        "family": info_cultivo["family"],
        "type": info_cultivo["type"],
        "agronomic_profile": {
            "practiced_cycles": info_cultivo["practiced_cycles"],
            "cycle_days": info_cultivo["cycle_days"],
            "optimal_temperature_c": info_cultivo["optimal_temperature_c"],
            "water": info_cultivo["water"],
            "care_guidelines": info_cultivo["care_guidelines"]
        },
        "planting_viability": viabilidad,
        "vulnerability_score": puntaje_riesgo,
        "total_pests_registered_in_country": len(plagas_coincidentes),
        "pests_analyzed": len(analisis_plagas_cultivo),
        "crop_alerts_summary": {
            "critical_risk": conteo_critico,
            "high_risk": conteo_alto,
            "medium_risk": conteo_medio,
            "low_risk": conteo_bajo
        },
        "pests_detail": analisis_plagas_cultivo
    }

    item_ranking = {
        "crop_id": info_cultivo["id"],
        "crop_eppocode": eppo_cultivo,
        "crop": info_cultivo["common_name_en"],
        "viability": viabilidad,
        "vulnerability_score": puntaje_riesgo,
        "critical_alerts": conteo_critico,
        "high_alerts": conteo_alto
    }

    return resumen_cultivo, item_ranking


def generar_reporte_multicultivo(
    cultivo_a_revisar: dict | list[dict],
    iso_pais: str = "MX",
    lat: float = 25.6866,
    lon: float = -100.3161,
    limite_plagas_por_cultivo: int | None = None,
    ruta_plagas_json: str = RUTA_PLAGAS_MX,
    max_workers_plagas: int = 4
) -> dict:
    """
    Receives a single crop JSON object (dict) or a list of crop JSON objects (list[dict])
    and processes them one by one, generating the complete report in English.
    """
    if isinstance(cultivo_a_revisar, dict):
        lista_cultivos = [cultivo_a_revisar]
    elif isinstance(cultivo_a_revisar, list):
        lista_cultivos = cultivo_a_revisar
    else:
        raise ValueError("cultivo_a_revisar must be a JSON object (dict) or a list of objects (list[dict]).")

    iso_pais = iso_pais.upper()

    # 1. Load shared resources once (local plagas-MX.json + Meteomatics weather series)
    catalogo_pais = cargar_plagas_locales(ruta_plagas_json)
    serie_clima = obtener_clima_meteomatics(lat, lon)

    resumen_clima = {
        "extreme_max_temp_C": max(d["t_max"] for d in serie_clima),
        "extreme_min_temp_C": min(d["t_min"] for d in serie_clima),
        "avg_relative_humidity_pct": round(sum(d["humidity"] for d in serie_clima) / len(serie_clima), 1),
        "high_rain_prob_days": sum(1 for d in serie_clima if d["rain_prob"] >= 50.0),
        "daily_series": serie_clima
    }

    cache_plagas_evaluadas = {}
    reportes_por_cultivo = []
    ranking_viabilidad = []

    # 2. Process each crop object one by one
    for idx_c, obj_cultivo in enumerate(lista_cultivos, start=1):
        nombre_log = obj_cultivo.get("nombre") if isinstance(obj_cultivo, dict) else str(obj_cultivo)
        eppo_log = obj_cultivo.get("eppocode") if isinstance(obj_cultivo, dict) else str(obj_cultivo)

        print(f"\n==========================================")
        print(f"[{idx_c}/{len(lista_cultivos)}] ANALYZING CROP OBJECT: {nombre_log} ({eppo_log})")
        print(f"==========================================")

        resumen_cultivo, item_ranking = procesar_cultivo_individual(
            cultivo_a_revisar=obj_cultivo,
            catalogo_pais=catalogo_pais,
            serie_clima=serie_clima,
            lat=lat,
            lon=lon,
            limite_plagas_por_cultivo=limite_plagas_por_cultivo,
            cache_plagas_evaluadas=cache_plagas_evaluadas,
            iso_pais=iso_pais,
            max_workers_plagas=max_workers_plagas
        )

        reportes_por_cultivo.append(resumen_cultivo)
        ranking_viabilidad.append(item_ranking)

    ranking_viabilidad.sort(key=lambda x: x["vulnerability_score"])

    return {
        "report_metadata": {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "queried_country_iso": iso_pais,
            "country_presence_source": os.path.basename(ruta_plagas_json),
            "coordinates": {"latitude": lat, "longitud": lon},
            "total_crops_evaluated": len(reportes_por_cultivo),
            "queried_crops": [
                {
                    "id": r["crop_id"],
                    "name_en": r["common_name_en"],
                    "name_es": r["common_name_es"],
                    "eppocode": r["crop_eppocode"]
                }
                for r in reportes_por_cultivo
            ],
            "total_unique_pests_in_cache": len(cache_plagas_evaluadas)
        },
        "planting_rotation_recommendation_ranking": ranking_viabilidad,
        "meteorological_context_10_days": resumen_clima,
        "crop_by_crop_analysis": reportes_por_cultivo
    }


if __name__ == "__main__":
    try:
        cultivo_a_revisar = {
            # Sugeto a cambios
            # "id": "maiz-grano",
            # "nombre": "Maíz grano",
            # "eppocode": "ZEAMS",
            # "unidad": "Tonelada",
            # "tipo": "Cereal",
            # "cientifico": "Zea mays",
            # "familia": "Poaceae",
            # "fija_nitrogeno": False,
            # "perenne": False,
            # "ciclos_practicados": [
            #     "PV",
            #     "OI"
            # ],
            # "ciclo_dias": [
            #     120,
            #     150
            # ],
            # "agua": {
            #     "consumo": "medio",
            #     "lluvia_optima_mm": [
            #         600,
            #         1200
            #     ],
            #     "lluvia_absoluta_mm": [
            #         400,
            #         1800
            #     ]
            # },
            # "temperatura_optima_c": [
            #     18,
            #     33
            # ],
            # "temperatura_absoluta_c": [
            #     10,
            #     47
            # ],
            # "ph_optimo": [
            #     5,
            #     7
            # ],
            # "ph_absoluto": [
            #     4.5,
            #     8.5
            # ],
            # "altitud_max_m": 4000,
            # "descripcion": "Cultivo base de la alimentación en México y el de mayor superficie del país. Se siembra en casi todos los municipios, tanto en temporal como en riego, y tiene una gran diversidad de variedades e híbridos adaptados a cada región.",
            # "suelo": "Francos, profundos y bien drenados; pH 5.5 a 7.5.",
            # "cuidados": [
            #     "Sembrar con el suelo húmedo; en temporal, al establecerse las lluvias.",
            #     "Demanda mucho nitrógeno: fraccionar la fertilización entre la siembra y la etapa de 6 a 8 hojas.",
            #     "Los periodos críticos de agua son la floración (espigamiento y jiloteo) y el llenado de grano.",
            #     "Controlar malezas en los primeros 30 a 40 días.",
            #     "Vigilar gusano cogollero y rotar con leguminosas para cortar el ciclo de plagas."
            # ],
            # "texto_revisado": False,
            # "nacional": {
            #     "superficie_sembrada_prom_ha": 7186815.5,
            #     "rend_p50": 3.82,
            #     "pmr_real_p50": 5489.0,
            #     "n_municipios": 2388
            # },
            # "fuentes": [
            #     "SIAP",
            #     "EcoCrop",
            #     "Curado"
            # ]
        }

        reporte = generar_reporte_multicultivo(
            cultivo_a_revisar=cultivo_a_revisar,
            iso_pais="MX",
            lat=22.7166910,
            lon=-102.7095870,
        )

        output_json = json.dumps(reporte, indent=2, ensure_ascii=False)
        ruta_salida = os.path.join(DIRECTORIO_ACTUAL, "reporte_multicultivo.json")

        with open(ruta_salida, "w", encoding="utf-8") as f:
            f.write(output_json)

        print(f"\n=== MULTI-CROP REPORT SUCCESSFULLY GENERATED ===")
        print(f"File saved at: {ruta_salida}")
        print("\nPlanting Viability Ranking:")
        for pos, item in enumerate(reporte["planting_rotation_recommendation_ranking"], start=1):
            print(
                f"  {pos}. {item['crop']} ({item['crop_eppocode']}) -> {item['viability']} "
                f"[Critical: {item['critical_alerts']} | High: {item['high_alerts']}]"
            )

    except Exception as e:
        print(f"\nError generating report: {e}")