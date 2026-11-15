"""Alertas para Principal: riesgos del clima y condiciones favorables para plagas y enfermedades.

Son reglas sencillas sobre el pronóstico de la semana y el clima de hoy. NO detectan plagas: avisan
que las condiciones las favorecen, para que el agricultor revise sus cultivos. Por eso el texto
siempre dice "condiciones favorables" y nunca "hay plaga". Los umbrales son valores agronómicos
generales; cuando el equipo de Cultivos tenga el catálogo con rangos por cultivo se pueden afinar.
"""

from datetime import date

DIAS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ORDEN_NIVEL = {"alta": 0, "media": 1, "baja": 2}

# Tipos de cultivo (del catálogo del Planificador) a los que aplica cada riesgo
TIPOS_HONGOS = {"cereal", "leguminosa", "hortaliza", "frutal", "oleaginosa"}
TIPOS_CHUPADORES = {"hortaliza", "leguminosa", "oleaginosa", "frutal"}
ENFERMEDAD_POR_TIPO = {
    "cereal": "rust and leaf spots",
    "leguminosa": "rust and anthracnose",
    "hortaliza": "blight and downy mildew",
}


def _nombre_dia(fecha: str, hoy: date) -> str:
    d = date.fromisoformat(fecha)
    return "today" if d == hoy else f"on {DIAS[d.weekday()]}"


def _alerta(id_: str, tipo: str, nivel: str, titulo: str, detalle: str, cultivos: list[str] | None = None) -> dict:
    return {"id": id_, "tipo": tipo, "nivel": nivel, "titulo": titulo, "detalle": detalle, "cultivos": cultivos or []}


def _del_clima(dias: list[dict], hoy_clima: dict, hoy: date) -> list[dict]:
    alertas = []

    con_minima = [d for d in dias if d["tmin"] is not None]
    if con_minima:
        d = min(con_minima, key=lambda x: x["tmin"])
        if d["tmin"] <= 2:
            alertas.append(_alerta(
                "helada", "clima", "alta" if d["tmin"] <= 0 else "media",
                f"Frost risk {_nombre_dia(d['fecha'], hoy)}",
                f"Low of {d['tmin']} °C. Protect sensitive crops and avoid watering at night.",
            ))

    con_maxima = [d for d in dias if d["tmax"] is not None]
    if con_maxima:
        d = max(con_maxima, key=lambda x: x["tmax"])
        if d["tmax"] >= 35:
            alertas.append(_alerta(
                "calor", "clima", "alta" if d["tmax"] >= 38 else "media",
                f"Extreme heat {_nombre_dia(d['fecha'], hoy)}",
                f"High of {d['tmax']} °C. Water early in the morning or at dusk to reduce plant stress.",
            ))

    con_lluvia = [d for d in dias if d["lluvia"] is not None]
    if con_lluvia:
        d = max(con_lluvia, key=lambda x: x["lluvia"])
        if d["lluvia"] >= 80:
            alertas.append(_alerta(
                "lluvia", "clima", "media",
                f"Rain likely {_nombre_dia(d['fecha'], hoy)}",
                f"{d['lluvia']}% chance. Consider postponing fertilizing or applying products.",
            ))

    viento = hoy_clima.get("vientoKmh")
    if viento is not None and viento >= 40:
        alertas.append(_alerta(
            "viento", "clima", "media", "Strong wind today",
            f"Gusts of {viento} km/h. Do not apply agrochemicals and check structures and netting.",
        ))
    return alertas


def _de_plagas(dias: list[dict], hoy_clima: dict, cultivos: list[dict]) -> list[dict]:
    if not cultivos:
        return []
    temp = hoy_clima.get("temperatura")
    humedad = hoy_clima.get("humedad")
    dias_de_lluvia = sum(1 for d in dias if (d["lluvia"] or 0) >= 60)
    maxima = max((d["tmax"] for d in dias if d["tmax"] is not None), default=None)

    def de_tipo(tipos: set[str]) -> list[dict]:
        return [c for c in cultivos if c["tipo"] in tipos]

    def nombres(lista: list[dict]) -> list[str]:
        return list(dict.fromkeys(c["nombre"] for c in lista))

    alertas = []

    # Hongos: humedad alta o varios días de lluvia con temperaturas templadas
    humedo = (humedad is not None and humedad >= 80) or dias_de_lluvia >= 2
    templado = temp is not None and 12 <= temp <= 28
    afectados = de_tipo(TIPOS_HONGOS)
    if humedo and templado and afectados:
        enfermedades = list(dict.fromkeys(ENFERMEDAD_POR_TIPO.get(c["tipo"], "foliar fungi") for c in afectados))
        alertas.append(_alerta(
            "hongos", "plaga", "media",
            "Conditions favorable for fungal diseases",
            f"Humidity and temperature favor {' and '.join(enfermedades)}. "
            "Check leaves and stems, and avoid sprinkler irrigation late in the day.",
            nombres(afectados),
        ))

    # Chupadores (pulgón, mosca blanca, trips, araña roja): calor y ambiente seco
    seco_y_calido = (temp is not None and temp >= 26 and humedad is not None and humedad < 50) or (
        maxima is not None and maxima >= 32 and dias_de_lluvia == 0
    )
    afectados = de_tipo(TIPOS_CHUPADORES)
    if seco_y_calido and afectados:
        alertas.append(_alerta(
            "chupadores", "plaga", "media",
            "Conditions favorable for aphids, whiteflies and spider mites",
            "Heat and dry air speed up their reproduction. Check the underside of leaves.",
            nombres(afectados),
        ))

    # Gusano cogollero: maíz con calor
    maiz = [c for c in cultivos if any(k in c["nombre"].lower().replace("í", "i") for k in ("corn", "maiz", "maize"))]
    if maiz and maxima is not None and maxima >= 28:
        alertas.append(_alerta(
            "cogollero", "plaga", "media",
            "Conditions favorable for fall armyworm",
            "Warm temperatures activate it in the corn whorl. Check young plants and leaf damage.",
            nombres(maiz),
        ))
    return alertas


def calcular(clima: dict, activos: list[dict], hoy: date) -> list[dict]:
    """Alertas ordenadas por gravedad. `clima` es lo que devuelve meteomatics.clima y `activos` las
    siembras en curso (planificador.siembras_en_curso)."""
    dias = [d for d in clima["pronostico"] if date.fromisoformat(d["fecha"]) >= hoy]
    cultivos = [
        {"nombre": a["cultivo"]["nombre"], "tipo": a["cultivo"]["tipo"]} for a in activos
    ]
    alertas = _del_clima(dias, clima["hoy"], hoy) + _de_plagas(dias, clima["hoy"], cultivos)
    return sorted(alertas, key=lambda a: ORDEN_NIVEL[a["nivel"]])  # estable: clima antes que plagas
