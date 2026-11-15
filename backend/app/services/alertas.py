"""Alertas para Principal: riesgos del clima y condiciones favorables para plagas y enfermedades.

Son reglas sencillas sobre el pronóstico de la semana y el clima de hoy. NO detectan plagas: avisan
que las condiciones las favorecen, para que el agricultor revise sus cultivos. Por eso el texto
siempre dice "condiciones favorables" y nunca "hay plaga".

Helada y calor se miden contra lo que tolera cada cultivo en curso (rango de temperatura del
catálogo de Cultivos, EcoCrop). Si un cultivo no viene del catálogo, o no hay cultivos en curso, se
usan umbrales generales. Los de plagas siguen siendo reglas generales por tipo de cultivo.

La falta de lluvia compara la lluvia observada en los últimos 30 días (NASA POWER) con lo que el
cultivo necesita por día en su ciclo (rango de lluvia ideal del catálogo entre los días del ciclo);
no sabe si hay riego, por eso lo dice así. El riesgo de encharcamiento solo se avisa a los cultivos
que el catálogo marca como sensibles cuando el pronóstico trae lluvia fuerte.
"""

from datetime import date

DIAS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ORDEN_NIVEL = {"alta": 0, "media": 1, "baja": 2}
MARGEN = 3  # °C antes del límite del cultivo en que ya se avisa (nivel "media")
DIAS_MINIMOS_LLUVIA = 10  # días con dato de lluvia observada para juzgar si hay déficit
DEFICIT_ALTO = 0.5  # lluvia observada / necesaria por debajo de esto: nivel "alta"
DEFICIT_MEDIO = 0.75  # y por debajo de esto: nivel "media"

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


def _en_riesgo(temperatura: float, cultivos: list[dict], clave: str, frio: bool) -> list[tuple[dict, str]]:
    """Cultivos en riesgo con esa temperatura y su nivel. Usa el límite del cultivo (si lo tiene) o el general."""
    resultado = []
    for c in cultivos:
        limite = c[clave]
        if limite is None:  # sin ficha: umbrales generales (helada: 0 y 2 °C; calor: 38 y 35 °C)
            alta, media = (0, 2) if frio else (38, 35)
        elif frio:
            alta, media = limite, limite + MARGEN
        else:
            alta, media = limite, limite - MARGEN
        peor = temperatura <= alta if frio else temperatura >= alta
        cerca = temperatura <= media if frio else temperatura >= media
        if peor:
            resultado.append((c, "alta"))
        elif cerca:
            resultado.append((c, "media"))
    return resultado


def _etiqueta(c: dict, clave: str, frio: bool) -> str:
    limite = c[clave]
    if limite is None:
        return c["nombre"]
    return f"{c['nombre']} (tolerates {'down to' if frio else 'up to'} {limite:g} °C)"


def _del_clima(dias: list[dict], hoy_clima: dict, hoy: date, cultivos: list[dict]) -> list[dict]:
    alertas = []

    con_minima = [d for d in dias if d["tmin"] is not None]
    if con_minima:
        d = min(con_minima, key=lambda x: x["tmin"])
        cuando = _nombre_dia(d["fecha"], hoy)
        if not cultivos:
            if d["tmin"] <= 2:
                alertas.append(_alerta(
                    "helada", "clima", "alta" if d["tmin"] <= 0 else "media", f"Frost risk {cuando}",
                    f"Low of {d['tmin']} °C. Protect sensitive crops and avoid watering at night.",
                ))
        else:
            riesgo = _en_riesgo(d["tmin"], cultivos, "frio", True)
            if riesgo:
                alertas.append(_alerta(
                    "helada", "clima", "alta" if any(n == "alta" for _, n in riesgo) else "media",
                    f"Frost risk {cuando}",
                    f"Low of {d['tmin']} °C, too close to what your crops tolerate: "
                    f"{', '.join(_etiqueta(c, 'frio', True) for c, _ in riesgo)}. "
                    "Protect them and avoid watering at night.",
                    [c["nombre"] for c, _ in riesgo],
                ))

    con_maxima = [d for d in dias if d["tmax"] is not None]
    if con_maxima:
        d = max(con_maxima, key=lambda x: x["tmax"])
        cuando = _nombre_dia(d["fecha"], hoy)
        if not cultivos:
            if d["tmax"] >= 35:
                alertas.append(_alerta(
                    "calor", "clima", "alta" if d["tmax"] >= 38 else "media", f"Extreme heat {cuando}",
                    f"High of {d['tmax']} °C. Water early in the morning or at dusk to reduce plant stress.",
                ))
        else:
            riesgo = _en_riesgo(d["tmax"], cultivos, "calor", False)
            if riesgo:
                alertas.append(_alerta(
                    "calor", "clima", "alta" if any(n == "alta" for _, n in riesgo) else "media",
                    f"Heat risk for your crops {cuando}",
                    f"High of {d['tmax']} °C, too close to what your crops tolerate: "
                    f"{', '.join(_etiqueta(c, 'calor', False) for c, _ in riesgo)}. "
                    "Water early in the morning or at dusk to reduce plant stress.",
                    [c["nombre"] for c, _ in riesgo],
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


def _de_lluvia_por_cultivo(dias: list[dict], reciente: dict | None, cultivos: list[dict], hoy: date) -> list[dict]:
    alertas = []
    con_lluvia = [d for d in dias if d["lluvia"] is not None]
    mayor_probabilidad = max(con_lluvia, key=lambda x: x["lluvia"]) if con_lluvia else None

    # Falta de lluvia: lo observado contra lo que necesita cada cultivo por día
    if reciente and (reciente.get("dias") or 0) >= DIAS_MINIMOS_LLUVIA and reciente.get("lluviaMm") is not None:
        por_dia = reciente["lluviaMm"] / reciente["dias"]
        deficit = []
        for c in cultivos:
            if c["lluvia_dia"]:
                proporcion = por_dia / c["lluvia_dia"]
                if proporcion < DEFICIT_ALTO:
                    deficit.append((c, "alta"))
                elif proporcion < DEFICIT_MEDIO:
                    deficit.append((c, "media"))
        if deficit:
            viene_lluvia = mayor_probabilidad and mayor_probabilidad["lluvia"] >= 70
            nota = (
                f" Rain is forecast ({mayor_probabilidad['lluvia']}% chance), so check again before irrigating."
                if viene_lluvia else " Consider irrigating if you can."
            )
            alertas.append(_alerta(
                "sequia", "clima", "alta" if any(n == "alta" for _, n in deficit) else "media",
                "Rain deficit for your crops",
                f"Only {reciente['lluviaMm']:g} mm fell in the last {reciente['dias']} days ({por_dia:.1f} mm a day). "
                f"They need more: {', '.join(f'{c['nombre']} (about {c['lluvia_dia']:.1f} mm a day)' for c, _ in deficit)}."
                + nota,
                [c["nombre"] for c, _ in deficit],
            ))

    # Encharcamiento: lluvia fuerte y cultivos sensibles al suelo anegado
    sensibles = [c for c in cultivos if c["encharca"]]
    if mayor_probabilidad and mayor_probabilidad["lluvia"] >= 80 and sensibles:
        alertas.append(_alerta(
            "encharcamiento", "clima", "media",
            f"Waterlogging risk {_nombre_dia(mayor_probabilidad['fecha'], hoy)}",
            f"{mayor_probabilidad['lluvia']}% chance of heavy rain. Sensitive to waterlogged soil: "
            f"{', '.join(c['nombre'] for c in sensibles)}. Make sure water can drain and hold off on irrigating.",
            [c["nombre"] for c in sensibles],
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


def _limites(ficha: dict | None) -> tuple[float | None, float | None]:
    """Temperatura mínima y máxima que tolera el cultivo (rango absoluto del catálogo), si se conoce."""
    rango = (ficha or {}).get("temperatura_absoluta_c")
    return (rango[0], rango[1]) if rango and len(rango) == 2 else (None, None)


def _lluvia_por_dia(ficha: dict | None) -> float | None:
    """Lluvia mínima ideal por día durante el ciclo (mm); None si el catálogo no trae el dato o es perenne."""
    ficha = ficha or {}
    ideal = (ficha.get("agua") or {}).get("lluvia_optima_mm")
    ciclo = ficha.get("ciclo_dias")
    if not ideal or not ciclo or ficha.get("perenne"):
        return None
    return ideal[0] / (sum(ciclo) / len(ciclo))


def calcular(clima: dict, activos: list[dict], hoy: date, fichas: dict | None = None,
             lluvia_reciente: dict | None = None) -> list[dict]:
    """Alertas ordenadas por gravedad. `clima` es lo que devuelve meteomatics.clima, `activos` las
    siembras en curso (planificador.siembras_en_curso), `fichas` las fichas del catálogo de esos
    cultivos por id (catalogo_cultivos.fichas_de; sin ellas se usan umbrales generales) y
    `lluvia_reciente` la lluvia observada de los últimos 30 días (nasa_power.periodo)."""
    dias = [d for d in clima["pronostico"] if date.fromisoformat(d["fecha"]) >= hoy]
    fichas = fichas or {}
    cultivos = []
    vistos = set()
    for a in activos:
        if a["cultivo"]["nombre"] in vistos:  # el mismo cultivo en varias parcelas cuenta una vez
            continue
        vistos.add(a["cultivo"]["nombre"])
        ficha = fichas.get(a["cultivo"].get("catalogo_id"))
        frio, calor = _limites(ficha)
        cultivos.append({
            "nombre": a["cultivo"]["nombre"], "tipo": a["cultivo"]["tipo"], "frio": frio, "calor": calor,
            "lluvia_dia": _lluvia_por_dia(ficha),
            "encharca": (ficha or {}).get("tolerancia_encharcamiento") in ("sensible", "sensitive"),
        })
    alertas = (
        _del_clima(dias, clima["hoy"], hoy, cultivos)
        + _de_lluvia_por_cultivo(dias, lluvia_reciente, cultivos, hoy)
        + _de_plagas(dias, clima["hoy"], cultivos)
    )
    return sorted(alertas, key=lambda a: ORDEN_NIVEL[a["nivel"]])  # estable: clima antes que plagas
