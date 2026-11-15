import os
import json
import math
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

# ==========================================
# 1. CONFIGURACIÓN Y CREDENCIALES
# ==========================================
EPPO_API_KEY = "575975242e06415e9d70269f24c4df10"
EPPO_BASE_URL = "https://api.eppo.int/gd/v2"
EPPO_HEADERS = {
    "X-Api-Key": EPPO_API_KEY,
    "Accept": "application/json"
}

METEO_USER = "hackathon_nasa_space_apps_esquivel_eder"
METEO_PASS = "52aV0CsnXHf4GwfRj3Lc"
METEO_BASE_URL = "https://api.meteomatics.com"

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))


# ==========================================
# 2. FUNCIONES DE CONSULTA A EPPO API v2
# ==========================================
def get_eppo(endpoint_path: str):
    """Petición GET a https://api.eppo.int/gd/v2/..."""
    url = f"{EPPO_BASE_URL}/{endpoint_path.lstrip('/')}"
    resp = requests.get(url, headers=EPPO_HEADERS, timeout=20)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def extraer_diccionarios(data) -> list[dict]:
    """Extrae listas de objetos sin importar el nivel de anidación del JSON de EPPO."""
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


def obtener_info_cultivo(eppo_cultivo: str) -> dict:
    """Obtiene el nombre científico y en español del cultivo evaluado."""
    nombre_cientifico = eppo_cultivo
    nombre_es = None
    try:
        nombres_raw = get_eppo(f"taxons/taxon/{eppo_cultivo}/names")
        registros = extraer_diccionarios(nombres_raw)
        for n in registros:
            idioma = str(n.get("isolang") or n.get("lang") or "").lower()
            nom = n.get("fullname") or n.get("name")
            if not nom:
                continue
            if idioma in ("la", "") and nombre_cientifico == eppo_cultivo:
                nombre_cientifico = nom
            elif idioma.startswith("es") and not nombre_es:
                nombre_es = nom
        if nombre_cientifico == eppo_cultivo and registros:
            nombre_cientifico = registros[0].get("fullname") or eppo_cultivo
    except Exception:
        pass

    return {
        "eppocode": eppo_cultivo,
        "nombre_cientifico": nombre_cientifico,
        "nombre_comun_es": nombre_es or nombre_cientifico
    }


def obtener_plagas_pais_eppo(iso_pais: str = "MX") -> dict[str, dict]:
    """
    Descarga una sola vez todas las plagas presentes en el país desde EPPO API v2.
    """
    iso_pais = iso_pais.upper()
    print(f"1. Consultando catálogo nacional de plagas en EPPO API para el país: {iso_pais}...")

    datos_presencia = get_eppo(f"country/{iso_pais}/presence")
    if datos_presencia is None:
        datos_presencia = get_eppo(f"countries/country/{iso_pais}/presence")

    catalogo_pais = {}
    if datos_presencia is not None:
        for reg in extraer_diccionarios(datos_presencia):
            codigo = reg.get("eppocode") or reg.get("code")
            if codigo:
                estado = str(
                    reg.get("status")
                    or reg.get("distribstatus")
                    or reg.get("label")
                    or f"Presente en {iso_pais}"
                )
                if "absent" not in estado.lower():
                    catalogo_pais[codigo.upper()] = {
                        "eppocode": codigo.upper(),
                        "estado_pais": estado,
                        "datos_eppo_pais": reg
                    }

    print(f"   ✔ API de EPPO respondió: {len(catalogo_pais)} plagas activas en {iso_pais}.")
    return catalogo_pais


def verificar_distribucion_taxon_pais(eppo_plaga: str, iso_pais: str = "MX") -> dict | None:
    """Respaldo individual si el endpoint masivo de país no devolvió datos."""
    dist_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/distribution")
    if not dist_raw:
        return None

    for d in extraer_diccionarios(dist_raw):
        pais = str(
            d.get("country") or d.get("isocode") or d.get("country_iso") or d.get("countrycode") or ""
        ).upper()
        estado = str(d.get("status") or d.get("distribstatus") or "Presente").strip()

        if pais == iso_pais.upper() and "absent" not in estado.lower():
            return {
                "eppocode": eppo_plaga.upper(),
                "estado_pais": estado,
                "datos_eppo_pais": d
            }
    return None


def obtener_expediente_completo_plaga(eppo_plaga: str, info_base: dict, info_pais: dict) -> dict:
    """Consulta los endpoints de Taxón en EPPO v2 para armar el expediente de la plaga."""
    tipo_biologico = "HONGO"
    familia_taxonomica = "No especificada"
    try:
        reino_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/kingdom")
        texto_reino = str(reino_raw).lower()
        if any(k in texto_reino for k in ["animalia", "insecta", "arthropoda", "acari", "nematoda"]):
            tipo_biologico = "INSECTO"
        elif any(k in texto_reino for k in ["fungi", "chromista", "oomycota"]):
            tipo_biologico = "HONGO"
        elif any(k in texto_reino for k in ["bacteria", "virus", "viroid", "phytoplasma"]):
            tipo_biologico = "PATOGENO_VECTOR"

        tax_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/taxonomy")
        for t in extraer_diccionarios(tax_raw):
            nivel = str(t.get("rank") or t.get("level") or "").lower()
            if "famil" in nivel or "order" in nivel:
                familia_taxonomica = t.get("fullname") or t.get("prefname") or familia_taxonomica
    except Exception:
        pass

    nombre_cientifico = info_base.get("fullname") or info_base.get("prefname") or eppo_plaga
    nombres_es = []
    nombres_en = []
    try:
        nombres_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/names")
        for n in extraer_diccionarios(nombres_raw):
            idioma = str(n.get("isolang") or n.get("lang") or "").lower()
            nom = n.get("fullname") or n.get("name")
            if not nom:
                continue
            if idioma.startswith("es") and nom not in nombres_es:
                nombres_es.append(nom)
            elif idioma.startswith("en") and nom not in nombres_en:
                nombres_en.append(nom)
    except Exception:
        pass

    cultivos_afectados = []
    try:
        hosts_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/hosts")
        for h in extraer_diccionarios(hosts_raw):
            nom_host = h.get("fullname") or h.get("prefname")
            cod_host = h.get("eppocode")
            if nom_host and len(cultivos_afectados) < 6:
                item_str = f"{nom_host} ({cod_host})" if cod_host else nom_host
                if item_str not in cultivos_afectados:
                    cultivos_afectados.append(item_str)
    except Exception:
        pass

    vectores = []
    try:
        vec_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/vectors")
        for v in extraer_diccionarios(vec_raw)[:4]:
            nom_vec = v.get("fullname") or v.get("prefname") or v.get("eppocode")
            if nom_vec and nom_vec not in vectores:
                vectores.append(nom_vec)
    except Exception:
        pass

    control_biologico = []
    try:
        bcas_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/bcas")
        for b in extraer_diccionarios(bcas_raw)[:5]:
            nom_bca = b.get("fullname") or b.get("prefname") or b.get("eppocode")
            if nom_bca and nom_bca not in control_biologico:
                control_biologico.append(nom_bca)
    except Exception:
        pass

    estatus_cuarentena = []
    try:
        cat_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/categorization")
        for c in extraer_diccionarios(cat_raw)[:4]:
            lista_q = c.get("qlist") or c.get("list") or c.get("status")
            pais_q = c.get("country") or c.get("isocode") or c.get("rppo") or ""
            if lista_q:
                estatus_cuarentena.append(f"{pais_q}: {lista_q}".strip(": "))
    except Exception:
        pass

    fotos_urls = []
    try:
        photos_raw = get_eppo(f"taxons/taxon/{eppo_plaga}/photos")
        for p in extraer_diccionarios(photos_raw)[:3]:
            url_foto = p.get("url") or p.get("file") or p.get("thumb") or p.get("original")
            if url_foto and url_foto not in fotos_urls:
                fotos_urls.append(url_foto)
    except Exception:
        pass

    return {
        "eppocode": eppo_plaga,
        "nombre_cientifico": nombre_cientifico,
        "nombre_comun_es": nombres_es[0] if nombres_es else nombre_cientifico,
        "otros_nombres_es": nombres_es[1:4],
        "nombre_comun_en": nombres_en[0] if nombres_en else None,
        "tipo_biologico": tipo_biologico,
        "taxonomia_referencia": familia_taxonomica,
        "estatus_en_pais": info_pais.get("estado_pais", "Presente"),
        "alertas_cuarentena": estatus_cuarentena,
        "cultivos_huesped_evitar_rotacion": cultivos_afectados,
        "vectores_transmision": vectores,
        "control_biologico_recomendado": control_biologico,
        "fotos": fotos_urls
    }


# ==========================================
# 3. METEOMATICS: SERIE TEMPORAL 10 DÍAS
# ==========================================
def obtener_clima_meteomatics(lat: float, lon: float) -> list[dict]:
    url = (
        f"{METEO_BASE_URL}/today-3DT00:00:00Z--today+6DT00:00:00Z:P1D/"
        f"t_max_2m_24h:C,t_min_2m_24h:C,relative_humidity_2m:p,prob_precip_24h:p/"
        f"{lat},{lon}/json"
    )
    print("2. Consultando ventana climática (3 días pasados + 6 días futuros) en Meteomatics...")
    resp = requests.get(url, auth=HTTPBasicAuth(METEO_USER, METEO_PASS), timeout=20)
    resp.raise_for_status()
    datos = resp.json()

    dias = {}
    for param in datos.get("data", []):
        p_name = param["parameter"]
        for d in param["coordinates"][0]["dates"]:
            fecha = d["date"][:10]
            dias.setdefault(fecha, {"fecha": fecha})
            if p_name == "t_max_2m_24h:C":
                dias[fecha]["t_max"] = d["value"]
            elif p_name == "t_min_2m_24h:C":
                dias[fecha]["t_min"] = d["value"]
            elif p_name == "relative_humidity_2m:p":
                dias[fecha]["humedad"] = d["value"]
            elif p_name == "prob_precip_24h:p":
                dias[fecha]["prob_lluvia"] = d["value"]

    for f in dias:
        dias[f]["t_promedio"] = round((dias[f].get("t_max", 0) + dias[f].get("t_min", 0)) / 2.0, 1)

    return [dias[f] for f in sorted(dias.keys())]


# ==========================================
# 4. RADAR GEOESPACIAL (GBIF + iNaturalist)
# ==========================================
def limpiar_nombre_cientifico(nombre_eppo: str) -> str:
    partes = nombre_eppo.strip().split()
    if len(partes) >= 2:
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
    avistamientos_cercanos = []

    delta_lat = radio_km / 111.0
    delta_lon = radio_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    lat_min, lat_max = round(lat - delta_lat, 4), round(lat + delta_lat, 4)
    lon_min, lon_max = round(lon - delta_lon, 4), round(lon + delta_lon, 4)

    # A) Consulta en GBIF API
    try:
        gbif_url = "https://api.gbif.org/v1/occurrence/search"
        gbif_params = {
            "scientificName": especie,
            "decimalLatitude": f"{lat_min},{lat_max}",
            "decimalLongitude": f"{lon_min},{lon_max}",
            "hasCoordinate": "true",
            "limit": 30
        }
        resp_gbif = requests.get(gbif_url, params=gbif_params, timeout=12)
        if resp_gbif.status_code == 200:
            for reg in resp_gbif.json().get("results", []):
                r_lat = reg.get("decimalLatitude")
                r_lon = reg.get("decimalLongitude")
                if r_lat is not None and r_lon is not None:
                    dist = calcular_distancia_km(lat, lon, r_lat, r_lon)
                    if dist <= radio_km:
                        avistamientos_cercanos.append({
                            "fuente": "GBIF",
                            "distancia_km": dist,
                            "estado_provincia": reg.get("stateProvince") or reg.get("locality") or "Región cercana",
                            "fecha": str(reg.get("eventDate") or reg.get("year") or "Histórico")[:10],
                            "coordenadas": [r_lat, r_lon]
                        })
    except Exception:
        pass

    # B) Consulta en iNaturalist / Naturalista CONABIO API
    try:
        inat_url = "https://api.inaturalist.org/v1/observations"
        inat_params = {
            "taxon_name": especie,
            "lat": lat,
            "lng": lon,
            "radius": radio_km,
            "per_page": 20
        }
        resp_inat = requests.get(inat_url, params=inat_params, timeout=12)
        if resp_inat.status_code == 200:
            for obs in resp_inat.json().get("results", []):
                geojson = obs.get("geojson") or {}
                coords = geojson.get("coordinates")
                if coords and len(coords) == 2:
                    o_lon, o_lat = float(coords[0]), float(coords[1])
                    dist = calcular_distancia_km(lat, lon, o_lat, o_lon)
                    if dist <= radio_km:
                        avistamientos_cercanos.append({
                            "fuente": "Naturalista/iNat",
                            "distancia_km": dist,
                            "estado_provincia": obs.get("place_guess") or "Región cercana",
                            "fecha": str(obs.get("observed_on") or "Reciente")[:10],
                            "coordenadas": [o_lat, o_lon]
                        })
    except Exception:
        pass

    avistamientos_cercanos.sort(key=lambda x: x["distancia_km"])

    if avistamientos_cercanos:
        mas_cercano = avistamientos_cercanos[0]
        return {
            "detectada_en_radio_cercano": True,
            "radio_busqueda_km": radio_km,
            "total_registros_en_zona": len(avistamientos_cercanos),
            "distancia_al_avistamiento_mas_cercano_km": mas_cercano["distancia_km"],
            "ubicacion_mas_cercana": mas_cercano["estado_provincia"],
            "fecha_ultimo_registro": mas_cercano["fecha"],
            "muestra_avistamientos": avistamientos_cercanos[:3]
        }
    else:
        return {
            "detectada_en_radio_cercano": False,
            "radio_busqueda_km": radio_km,
            "total_registros_en_zona": 0,
            "distancia_al_avistamiento_mas_cercano_km": None,
            "ubicacion_mas_cercana": f"Sin reportes georreferenciados a menos de {radio_km} km",
            "fecha_ultimo_registro": None,
            "muestra_avistamientos": []
        }


# ==========================================
# 5. EVALUADOR UNITARIO DE PLAGA (CON CACHÉ)
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
    """
    Si la plaga ya se evaluó en un cultivo anterior, la recupera del caché al instante.
    Si es nueva, consulta EPPO + Radar GPS + Clima y la guarda en caché.
    """
    if cod in cache_plagas:
        print(f"      ⚡ {cod} recuperado de caché en memoria (plaga compartida entre cultivos).")
        return cache_plagas[cod]

    expediente = obtener_expediente_completo_plaga(cod, info_base, info_pais)
    tipo = expediente["tipo_biologico"]

    presencia_local = verificar_presencia_cercana_gps(
        expediente["nombre_cientifico"], lat, lon, radio_km=100.0
    )
    expediente["presencia_geografica_cercana"] = presencia_local

    racha = 0
    max_racha = 0
    gdd_total = 0.0
    dias_favorables_detalle = []

    for dia in serie_clima:
        t_max, t_min, t_med = dia["t_max"], dia["t_min"], dia["t_promedio"]
        hum, lluvia = dia["humedad"], dia["prob_lluvia"]

        if tipo in ("INSECTO", "PATOGENO_VECTOR"):
            gdd_dia = max(0.0, t_med - 10.0)
            gdd_total += gdd_dia
            condicion = (18.0 <= t_max <= 35.0) and (hum >= 40.0)
            motivo = f"Calor útil (+{round(gdd_dia, 1)} GDD) y {t_max}°C"
        else:
            condicion = (12.0 <= t_med <= 26.0) and (hum >= 80.0 or lluvia >= 50.0)
            motivo = f"Alta humedad ({hum}%) / Lluvia ({lluvia}%)"

        if condicion:
            racha += 1
            max_racha = max(max_racha, racha)
            dias_favorables_detalle.append({"fecha": dia["fecha"], "condicion": motivo})
        else:
            racha = 0

    if (tipo in ("INSECTO", "PATOGENO_VECTOR") and gdd_total >= 65.0) or (tipo == "HONGO" and max_racha >= 3):
        if presencia_local["detectada_en_radio_cercano"]:
            riesgo = "CRÍTICO"
            detalle_riesgo = "Clima favorable + Plaga confirmada a menos de 100 km de tus coordenadas"
            accion = (
                "Riesgo inminente de brote confirmado en tu región. Iniciar monitoreo en campo, "
                "liberar agentes de control biológico sugeridos y evitar rotar con los cultivos huésped listados."
            )
        else:
            riesgo = "ALTO"
            detalle_riesgo = "Clima favorable para incubación, pero sin avistamientos recientes en 100 km"
            accion = (
                "El clima favorece la incubación aunque no hay reportes cercanos recientes. "
                "Mantener vigilancia preventiva y revisar cultivos huésped."
            )
    elif (tipo in ("INSECTO", "PATOGENO_VECTOR") and gdd_total >= 45.0) or (tipo == "HONGO" and max_racha == 2):
        riesgo = "MEDIO"
        detalle_riesgo = "Condiciones climáticas parcialmente favorables"
        accion = "Vigilar envés de hojas y trampas de feromonas durante los días críticos."
    else:
        riesgo = "BAJO"
        detalle_riesgo = "Clima fuera del umbral de incubación"
        accion = "Condiciones climáticas actuales fuera del umbral óptimo de incubación masiva."

    expediente["evaluacion_climatica"] = {
        "nivel_riesgo": riesgo,
        "diagnostico_geografico_climatico": detalle_riesgo,
        "max_dias_consecutivos_favorables": max_racha,
        "grados_dia_desarrollo_GDD": round(gdd_total, 1),
        "dias_criticos_detectados": dias_favorables_detalle,
        "recomendacion_agronomica": accion
    }

    cache_plagas[cod] = expediente
    return expediente


# ==========================================
# 6. MOTOR MULTI-CULTIVO (CULTIVO POR CULTIVO)
# ==========================================
def generar_reporte_multicultivo(
    lista_cultivos: list[str] | str,
    iso_pais: str = "MX",
    lat: float = 25.6866,
    lon: float = -100.3161,
    limite_plagas_por_cultivo: int = 5
) -> dict:
    # Acepta tanto un string único ("ZEAMX") como una lista de cultivos (["ZEAMX", "SOLTU"])
    if isinstance(lista_cultivos, str):
        lista_cultivos = [c.strip().upper() for c in lista_cultivos.split(",") if c.strip()]
    else:
        lista_cultivos = [str(c).strip().upper() for c in lista_cultivos if str(c).strip()]

    iso_pais = iso_pais.upper()

    # 1. Descargar recursos compartidos una sola vez (Presencia del país y Clima de las coordenadas)
    catalogo_pais = obtener_plagas_pais_eppo(iso_pais)
    serie_clima = obtener_clima_meteomatics(lat, lon)

    resumen_clima = {
        "temp_maxima_extrema_C": max(d["t_max"] for d in serie_clima),
        "temp_minima_extrema_C": min(d["t_min"] for d in serie_clima),
        "humedad_relativa_promedio_pct": round(sum(d["humedad"] for d in serie_clima) / len(serie_clima), 1),
        "dias_con_alta_prob_lluvia": sum(1 for d in serie_clima if d["prob_lluvia"] >= 50.0),
        "serie_diaria": serie_clima
    }

    # Caché global para no repetir llamadas si dos cultivos comparten la misma plaga
    cache_plagas_evaluadas = {}
    reportes_por_cultivo = []
    ranking_viabilidad = []
    orden_prioridad = {"CRÍTICO": 1, "ALTO": 2, "MEDIO": 3, "BAJO": 4}

    # 2. Iterar cultivo por cultivo
    for idx_c, eppo_cultivo in enumerate(lista_cultivos, start=1):
        print(f"\n==========================================")
        print(f"🌾 [{idx_c}/{len(lista_cultivos)}] ANALIZANDO CULTIVO: {eppo_cultivo}")
        print(f"==========================================")

        info_cultivo = obtener_info_cultivo(eppo_cultivo)
        plagas_cultivo_raw = get_eppo(f"taxons/taxon/{eppo_cultivo}/pests")
        lista_plagas_cultivo = extraer_diccionarios(plagas_cultivo_raw)

        plagas_coincidentes = []
        codigos_vistos = set()

        for p in lista_plagas_cultivo:
            cod = str(p.get("eppocode") or "").upper()
            if not cod or cod in codigos_vistos:
                continue

            if catalogo_pais:
                if cod in catalogo_pais:
                    codigos_vistos.add(cod)
                    plagas_coincidentes.append((cod, p, catalogo_pais[cod]))
            else:
                info_dist = verificar_distribucion_taxon_pais(cod, iso_pais)
                if info_dist:
                    codigos_vistos.add(cod)
                    plagas_coincidentes.append((cod, p, info_dist))
                    if len(plagas_coincidentes) >= limite_plagas_por_cultivo:
                        break

        print(f"   -> {len(plagas_coincidentes)} plagas de {info_cultivo['nombre_comun_es']} presentes en {iso_pais}.")

        analisis_plagas_cultivo = []
        seleccion = plagas_coincidentes[:limite_plagas_por_cultivo]

        for idx_p, (cod, info_base, info_pais) in enumerate(seleccion, start=1):
            print(f"   [{idx_p}/{len(seleccion)}] Evaluando plaga {cod} para {eppo_cultivo}...")
            expediente = evaluar_plaga_individual(
                cod, info_base, info_pais, serie_clima, lat, lon, cache_plagas_evaluadas
            )
            analisis_plagas_cultivo.append(expediente)

        analisis_plagas_cultivo.sort(
            key=lambda x: orden_prioridad.get(x["evaluacion_climatica"]["nivel_riesgo"], 5)
        )

        # Conteo de alertas para este cultivo específico
        conteo_critico = sum(1 for p in analisis_plagas_cultivo if p["evaluacion_climatica"]["nivel_riesgo"] == "CRÍTICO")
        conteo_alto = sum(1 for p in analisis_plagas_cultivo if p["evaluacion_climatica"]["nivel_riesgo"] == "ALTO")
        conteo_medio = sum(1 for p in analisis_plagas_cultivo if p["evaluacion_climatica"]["nivel_riesgo"] == "MEDIO")
        conteo_bajo = sum(1 for p in analisis_plagas_cultivo if p["evaluacion_climatica"]["nivel_riesgo"] == "BAJO")

        # Puntaje de vulnerabilidad (menor puntaje = cultivo más seguro para sembrar/rotar)
        puntaje_riesgo = (conteo_critico * 10) + (conteo_alto * 5) + (conteo_medio * 2)

        if conteo_critico > 0:
            viabilidad = "NO RECOMENDADO (Riesgo crítico de plagas activas en la zona)"
        elif conteo_alto > 0:
            viabilidad = "PRECAUCIÓN (Requiere manejo preventivo de plagas)"
        else:
            viabilidad = "ÓPTIMO PARA SIEMBRA / ROTACIÓN (Bajo riesgo fitosanitario actual)"

        resumen_cultivo = {
            "eppocode_cultivo": eppo_cultivo,
            "nombre_comun_es": info_cultivo["nombre_comun_es"],
            "nombre_cientifico": info_cultivo["nombre_cientifico"],
            "viabilidad_siembra": viabilidad,
            "puntaje_vulnerabilidad": puntaje_riesgo,
            "total_plagas_registradas_en_pais": len(plagas_coincidentes),
            "plagas_analizadas": len(analisis_plagas_cultivo),
            "resumen_alertas_cultivo": {
                "riesgo_critico": conteo_critico,
                "riesgo_alto": conteo_alto,
                "riesgo_medio": conteo_medio,
                "riesgo_bajo": conteo_bajo
            },
            "plagas_detalle": analisis_plagas_cultivo
        }

        reportes_por_cultivo.append(resumen_cultivo)
        ranking_viabilidad.append({
            "eppocode_cultivo": eppo_cultivo,
            "cultivo": info_cultivo["nombre_comun_es"],
            "viabilidad": viabilidad,
            "puntaje_vulnerabilidad": puntaje_riesgo,
            "alertas_criticas": conteo_critico,
            "alertas_altas": conteo_alto
        })

    # Ordenar el ranking desde el cultivo más seguro (menor puntaje) hasta el más riesgoso
    ranking_viabilidad.sort(key=lambda x: x["puntaje_vulnerabilidad"])

    return {
        "metadata_reporte": {
            "fecha_generacion_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pais_consultado_iso": iso_pais,
            "coordenadas": {"latitud": lat, "longitud": lon},
            "total_cultivos_evaluados": len(lista_cultivos),
            "cultivos_consultados": lista_cultivos,
            "total_plagas_unicas_en_cache": len(cache_plagas_evaluadas)
        },
        "ranking_recomendacion_siembra_rotacion": ranking_viabilidad,
        "contexto_meteorologico_10_dias": resumen_clima,
        "analisis_cultivo_por_cultivo": reportes_por_cultivo
    }


if __name__ == "__main__":
    try:
        # Lista de cultivos a revisar uno por uno:
        # ZEAMX = Maíz | SOLTU = Papa | LYPES = Tomate | PHSVX = Frijol
        cultivos_a_revisar  = ["ZEAMS", "TRZSP", "SORVU", "ORYSA", "HORVX", "AVESA", "PHSVX", "GLXMA", "CIEAR", "LENCU", "VICFX", "SOLTU", "LYPES", "CPSAN", "ALLCE", "ALLSA", "CUUPE", "CUMSA", "LACSA", "BRSOX", "DAUCA", "PEBAM", "CIDAF", "CIDSI", "MUBPA", "MABSD", "VITVI", "FRAAN", "SACOF", "GOSHI", "COFAR", "HELAN","MEDSA"]

        reporte = generar_reporte_multicultivo(
            lista_cultivos=cultivos_a_revisar,
            iso_pais="MX",
            lat=22.7166910,
            lon=-102.7095870,
            limite_plagas_por_cultivo=5
        )

        output_json = json.dumps(reporte, indent=2, ensure_ascii=False)
        ruta_salida = os.path.join(DIRECTORIO_ACTUAL, "reporte_multicultivo.json")

        with open(ruta_salida, "w", encoding="utf-8") as f:
            f.write(output_json)

        print(f"\n=== REPORTE MULTI-CULTIVO GENERADO CON ÉXITO ===")
        print(f"Archivo guardado en: {ruta_salida}")
        print("\nRanking de Viabilidad de Siembra (del más seguro al más riesgoso):")
        for pos, item in enumerate(reporte["ranking_recomendacion_siembra_rotacion"], start=1):
            print(
                f"  {pos}. {item['cultivo']} ({item['eppocode_cultivo']}) -> {item['viabilidad']} "
                f"[Críticas: {item['alertas_criticas']} | Altas: {item['alertas_altas']}]"
            )

    except Exception as e:
        print(f"\nError al generar el reporte multi-cultivo: {e}")