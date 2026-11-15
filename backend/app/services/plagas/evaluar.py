"""Reglas del motor de plagas: del expediente de EPPO y el clima a un nivel de riesgo. Sin red.

Son las reglas del motor de la rama `plagas`, ordenadas para poder probarlas:

- Insectos y vectores (y los patógenos que transmiten): suman grados-día (temperatura media menos 10 °C, solo si
  es positiva). Un día es favorable con máxima de 18 a 35 °C y humedad de 40 % o más. 65 grados-día o más en la
  ventana es clima favorable; 45 o más, parcialmente favorable.
- Hongos: un día es favorable con temperatura media de 12 a 26 °C y humedad de 80 % o más (o 50 % o más de
  probabilidad de lluvia). Tres días seguidos favorables es clima favorable; dos, parcialmente favorable.
- Con clima favorable el riesgo es "high"; sube a "critical" si hay registros de la plaga a menos de 100 km.
  Parcialmente favorable es "medium" y lo demás "low".

Son avisos para revisar el campo, no detecciones: nada de esto dice que la plaga esté en la parcela.
"""

from app.services.plagas.eppo import diccionarios

NIVELES = ("critical", "high", "medium", "low")
ORDEN = {nivel: i for i, nivel in enumerate(NIVELES)}

GDD_BASE = 10.0
GDD_ALTO = 65.0
GDD_MEDIO = 45.0

TIPOS = ("insect", "fungus", "pathogen")  # los que se pueden evaluar con clima; las malezas se omiten

# Estado de la plaga en el país (EPPO): de más a menos extendida, para elegir cuáles analizar primero
ESTADOS = {
    "A": "Present (widespread)",
    "B": "Present (restricted distribution)",
    "C": "Present (few occurrences)",
    "X": "Present (no details)",
    "T": "Transient",
    "G": "Present (under control / greenhouse)",
    "H": "Present (historical / doubtful record)",
    "J": "Present (interception / uncertain status)",
    "K": "Present (under review)",
}
PRIORIDAD_ESTADO = {e: i for i, e in enumerate("ABCXKGJHT")}

# Qué tan principal es el cultivo como hospedero de la plaga (`class_label` de EPPO). Se analizan las plagas con
# hospedero principal primero, luego las comunes; las experimentales y dudosas se omiten.
PRIORIDAD_CLASE = {"Major host": 0, "Host": 1}


def clase_de(plaga_de_cultivo: dict) -> int | None:
    """Prioridad de una plaga de la lista de un cultivo (0 la más relevante); None si no se debe analizar."""
    etiqueta = plaga_de_cultivo.get("class_label")
    return 1 if etiqueta is None else PRIORIDAD_CLASE.get(etiqueta)


def plagas_presentes(registros: list[dict]) -> dict[str, dict]:
    """Código EPPO -> datos de las plagas que sí están en el país (sin las ausentes ni las erradicadas)."""
    pais = {}
    for reg in registros:
        if not isinstance(reg, dict):
            continue
        codigo = str(reg.get("eppocode") or "").strip().upper()
        estado = str(reg.get("peststatus") or "X").strip().upper()
        if not codigo or estado in ("D", "E") or reg.get("yr_erad") is not None:
            continue
        texto = ESTADOS.get(estado, f"Present ({estado})")
        if reg.get("yr_situation"):
            texto = f"{texto} - Situation {reg['yr_situation']}"
        pais[codigo] = {"eppocode": codigo, "nombre": reg.get("prefname"), "estado": estado, "estadoPais": texto}
    return pais


def clasificar(reino: object) -> str:
    """Tipo biológico según el reino que da EPPO: insect, fungus, pathogen (bacteria, virus...) o weed."""
    texto = str(reino or "").lower()
    if any(k in texto for k in ("animalia", "insecta", "arthropoda", "acari", "nematoda")):
        return "insect"
    if any(k in texto for k in ("fungi", "chromista", "oomycota")):
        return "fungus"
    if any(k in texto for k in ("bacteria", "virus", "viroid", "phytoplasma")):
        return "pathogen"
    if "plantae" in texto:
        return "weed"
    return "fungus"  # sin dato claro, la regla más prudente es la de hongos (humedad y temperatura)


def evaluar_clima(tipo: str, serie: list[dict]) -> dict:
    """Días favorables, grados-día y nivel de clima (high, medium o low) de una plaga en la serie diaria."""
    racha = mejor_racha = 0
    gdd = 0.0
    favorables = []
    for dia in serie:
        if tipo == "fungus":
            favorable = 12.0 <= dia["tmed"] <= 26.0 and (dia["humedad"] >= 80.0 or dia["lluvia"] >= 50.0)
            motivo = f"High humidity ({dia['humedad']:.0f}%) / rain probability ({dia['lluvia']:.0f}%)"
        else:
            aporte = max(0.0, dia["tmed"] - GDD_BASE)
            gdd += aporte
            favorable = 18.0 <= dia["tmax"] <= 35.0 and dia["humedad"] >= 40.0
            motivo = f"Useful heat (+{aporte:.1f} degree-days) and {dia['tmax']:.0f}°C"
        if favorable:
            racha += 1
            mejor_racha = max(mejor_racha, racha)
            favorables.append({"fecha": dia["fecha"], "condicion": motivo})
        else:
            racha = 0

    if tipo == "fungus":
        nivel = "high" if mejor_racha >= 3 else "medium" if mejor_racha == 2 else "low"
    else:
        nivel = "high" if gdd >= GDD_ALTO else "medium" if gdd >= GDD_MEDIO else "low"
    return {"nivelClima": nivel, "rachaDias": mejor_racha, "gradosDia": round(gdd, 1), "diasFavorables": favorables}


def riesgo(clima: dict, presencia: dict) -> dict:
    """Nivel final, diagnóstico y recomendación a partir del clima y de los registros cercanos."""
    nivel = clima["nivelClima"]
    cerca = presencia["detectada"]
    if nivel == "high" and cerca:
        return {
            "nivel": "critical",
            "diagnostico": "Favorable weather and the pest has been recorded within 100 km of this location",
            "accion": "Start field monitoring now, consider the listed biological control agents and avoid rotating "
                      "with the host crops listed below.",
        }
    if nivel == "high":
        return {
            "nivel": "high",
            "diagnostico": "Favorable weather, but no recent records within 100 km",
            "accion": "Weather favors the pest even though nobody has reported it nearby. Keep preventive "
                      "surveillance and inspect host crops.",
        }
    if nivel == "medium":
        return {
            "nivel": "medium",
            "diagnostico": "Partially favorable weather",
            "accion": "Monitor the underside of leaves and pheromone traps on the warmest or most humid days.",
        }
    return {
        "nivel": "low",
        "diagnostico": "Weather outside the range this pest needs to build up",
        "accion": "Current conditions are outside the optimal range for a build-up.",
    }


def _idioma(n: dict) -> str:
    return str(n.get("lang_iso") or n.get("isolang") or n.get("lang") or "").lower()


def _nombres(respuesta, idioma: str) -> list[str]:
    salida = []
    for n in diccionarios(respuesta):
        nombre = n.get("fullname") or n.get("name")
        if nombre and _idioma(n).startswith(idioma) and nombre not in salida:
            salida.append(nombre)
    return salida


def _mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def _lista(respuesta, limite: int) -> list[str]:
    salida = []
    for d in diccionarios(respuesta):
        nombre = d.get("fullname") or d.get("prefname") or d.get("eppocode")
        if nombre and nombre not in salida:
            salida.append(nombre)
        if len(salida) >= limite:
            break
    return salida


def expediente(codigo: str, crudo: dict, pais: dict) -> dict:
    """Datos de la plaga que no dependen del lugar ni del clima, en inglés."""
    tipo = clasificar(crudo.get("kingdom"))
    nombres_en = _nombres(crudo.get("names"), "en")
    nombres_es = _nombres(crudo.get("names"), "es")

    cientifico = pais.get("nombre") or codigo
    latin = [n for n in diccionarios(crudo.get("names")) if _idioma(n) == "la" and (n.get("fullname") or n.get("name"))]
    if latin:  # el nombre en latín que EPPO marca como preferido (o el primero)
        elegido = next((n for n in latin if n.get("preferred")), latin[0])
        cientifico = elegido.get("fullname") or elegido.get("name")

    # Hospederos para no rotar con ellos: los principales; si no hay, unos pocos comunes. Sin los experimentales.
    todos = [h for h in diccionarios(crudo.get("hosts")) if (h.get("prefname") or h.get("fullname"))]
    principales = [h for h in todos if h.get("class_label") == "Major host"]
    comunes = [h for h in todos if h.get("class_label") in (None, "Host")][:3]
    hospederos = []
    for h in (principales or comunes)[:6]:
        nombre = h.get("prefname") or h.get("fullname")
        texto = f"{nombre} ({h['eppocode']})" if h.get("eppocode") else nombre
        if texto not in hospederos:
            hospederos.append(texto)

    # Estatus de cuarentena en México (EPPO lista decenas de países: solo el que le importa al agricultor)
    cuarentena = []
    for c in diccionarios(crudo.get("categorization")):
        if c.get("country_iso") == "MX" and (c.get("qlist_label") or c.get("qlist")):
            texto = f"Mexico: {c.get('qlist_label') or c.get('qlist')}"
            if texto not in cuarentena:
                cuarentena.append(texto)

    fotos = []
    for f in diccionarios(crudo.get("photos")):
        archivos = f.get("files") if isinstance(f.get("files"), list) else []
        grande = next((a.get("url") for a in archivos if isinstance(a, dict) and a.get("size") == "1024x0"), None)
        url = grande or next((a.get("url") for a in archivos if isinstance(a, dict) and a.get("url")), None) or f.get("url")
        if url and url not in fotos:
            fotos.append(url)
        if len(fotos) >= 3:
            break

    return {
        "eppocode": codigo,
        "nombre": _mayuscula(nombres_en[0]) if nombres_en else cientifico,
        "otrosNombres": [_mayuscula(n) for n in nombres_en[1:4]],
        "nombreEs": _mayuscula(nombres_es[0]) if nombres_es else None,
        "nombreCientifico": cientifico,
        "tipo": tipo,
        "estadoPais": pais.get("estadoPais", "Present"),
        "cuarentena": cuarentena,
        "hospederos": hospederos,
        "vectores": _lista(crudo.get("vectors"), 4),
        "controlBiologico": _lista(crudo.get("bcas"), 5),
        "fotos": fotos,
    }


def resumen(plagas: list[dict]) -> dict:
    """Conteo por nivel y el nivel más alto entre las plagas analizadas."""
    conteo = {n: sum(1 for p in plagas if p["riesgo"] == n) for n in NIVELES}
    peor = next((n for n in NIVELES if conteo[n]), "low")
    return {"nivel": peor, "conteo": conteo}
