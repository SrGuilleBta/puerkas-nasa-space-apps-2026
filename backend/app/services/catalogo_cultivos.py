"""Une el Planificador con el catálogo de Cultivos (backend/pipeline/cultivos).

El Planificador guarda sus propios cultivos (tabla `cultivo`) para que las siembras no cambien si
cambia el catálogo. Cuando el usuario elige un cultivo del catálogo se crea (o se reutiliza) una fila
con `catalogo_id`, que sirve para mostrar la ficha (cuidados, temperatura, agua, suelo...).
"""

import unicodedata

from app.db import clave
from app.services import cultivos as catalogo_servicio
from app.services import ecocrop, estados
from app.services.planificador import NoEncontrado, _cultivo_dict, _existe, _fila

CICLO_PERENNE = 365  # un frutal o pasto perenne se planea por año


def _catalogo() -> dict:
    """El catálogo precalculado por la pipeline; vacío si todavía no se generó."""
    try:
        return catalogo_servicio.catalogo()
    except catalogo_servicio.SinDatos:
        return {"cultivos": [], "por_id": {}}


# El catálogo puede traer el tipo en español ("Leguminosa") o, ya traducido, en inglés ("Legume").
TIPOS_EN_INGLES = {
    "legume": "leguminosa", "fruit": "frutal", "vegetable": "hortaliza", "oilseed": "oleaginosa",
    "forage": "forraje", "tuber": "tuberculo", "seed": "otro", "other": "otro",
}


def tipo_del_planificador(tipo: str | None) -> str:
    """El Planificador guarda el tipo en español, minúsculas y sin acentos ("leguminosa", "tuberculo"):
    las reglas de rotación y de plagas dependen de esos valores, venga como venga del catálogo."""
    if not tipo:
        return "otro"
    sin_acentos = unicodedata.normalize("NFKD", tipo).encode("ascii", "ignore").decode()
    tipo = sin_acentos.strip().lower()
    tipo = TIPOS_EN_INGLES.get(tipo, tipo)
    return "otro" if tipo in ("semilla", "") else tipo


def ciclo_de(ficha: dict) -> int:
    """Días del ciclo: el punto medio del rango del catálogo (o un año si es perenne)."""
    rango = ficha.get("ciclo_dias")
    if ficha.get("perenne") or not rango:
        return CICLO_PERENNE
    return max(1, round(sum(rango) / len(rango)))


def listar() -> list[dict]:
    """Lista ligera para el buscador de cultivos del popup de siembra."""
    return sorted(
        (
            {
                "id": c["id"],
                "nombre": c["nombre"],
                "tipo": tipo_del_planificador(c.get("tipo")),
                "ciclo_dias": ciclo_de(c),
                "perenne": bool(c.get("perenne")),
            }
            for c in _catalogo()["cultivos"]
        ),
        key=lambda c: clave(c["nombre"]),
    )


def asegurar_cultivo(con, catalogo_id: str) -> dict:
    """Devuelve el cultivo del Planificador que corresponde al del catálogo; lo crea si no existe."""
    ficha = _catalogo()["por_id"].get(catalogo_id)
    if ficha is None:
        raise NoEncontrado(f"The catalog has no crop \"{catalogo_id}\"")

    existente = _fila(con, "SELECT * FROM cultivo WHERE catalogo_id = ?", catalogo_id)
    if existente is None:
        existente = _fila(con, "SELECT * FROM cultivo WHERE clave = ?", clave(ficha["nombre"]))
        if existente is not None and existente["catalogo_id"] is None:
            with con:  # ya estaba con ese nombre (p. ej. lo escribió el usuario): se enlaza al catálogo
                con.execute("UPDATE cultivo SET catalogo_id = ? WHERE id = ?", (catalogo_id, existente["id"]))
    if existente is not None:
        return _cultivo_dict(_existe(con, "cultivo", existente["id"], "crop"))

    with con:
        id_ = con.execute(
            "INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias, catalogo_id) VALUES (?, ?, ?, ?, ?)",
            (ficha["nombre"], clave(ficha["nombre"]), tipo_del_planificador(ficha.get("tipo")),
             ciclo_de(ficha), catalogo_id),
        ).lastrowid
    return _cultivo_dict(_existe(con, "cultivo", id_, "crop"))


def sincronizar_nombres(con) -> None:
    """Pone en los cultivos enlazados el nombre actual del catálogo (si la pipeline lo cambió, p. ej.
    al traducirlo). Se salta el cambio si el nombre nuevo ya lo tiene otro cultivo."""
    for fila in con.execute("SELECT id, nombre, catalogo_id FROM cultivo WHERE catalogo_id IS NOT NULL").fetchall():
        datos = _catalogo()["por_id"].get(fila["catalogo_id"])
        if datos is None or datos["nombre"] == fila["nombre"]:
            continue
        if con.execute("SELECT 1 FROM cultivo WHERE clave = ? AND id != ?", (clave(datos["nombre"]), fila["id"])).fetchone():
            continue
        with con:
            con.execute("UPDATE cultivo SET nombre = ?, clave = ? WHERE id = ?",
                        (datos["nombre"], clave(datos["nombre"]), fila["id"]))


def mercado(catalogo_id: str | None, cve_ent: str | None) -> dict | None:
    """Precio, rendimiento y chips de un cultivo del catálogo según SIAP, para "Cultivos activos".

    Usa los datos del estado (`cve_ent`) y, si ahí no se siembra el cultivo o no se conoce el estado,
    los nacionales. El precio es el precio medio rural del último año de SIAP, en pesos de ese año, y
    `variacion_pct` lo compara con la mediana de los 10 años de la ventana. No hay un dato de demanda:
    la variación del precio es lo más cercano. None si el cultivo no viene del catálogo o no hay datos.
    """
    if not catalogo_id:
        return None
    claves = [cve_ent, "00"] if cve_ent else ["00"]
    try:
        ind, ubicacion = catalogo_servicio.indicadores_de(catalogo_id, claves)
    except catalogo_servicio.SinDatos:
        return None
    if ind is None:
        return None

    precio, rendimiento = ind.get("precio") or {}, ind.get("rendimiento") or {}
    ultimo, tipico = precio.get("pmr_real_ultimo"), precio.get("pmr_real_p50")
    variacion = round((ultimo / tipico - 1) * 100) if ultimo and tipico else None

    # Los chips salen de los campos estructurados (no del texto de las etiquetas de la pipeline)
    chips = []
    # La pipeline traducida da "high"/"low"; la anterior daba "alta"/"baja"/"alto": se aceptan las dos.
    nivel = (ind.get("rentabilidad") or {}).get("nivel")
    if nivel in ("high", "alta"):
        chips.append(("positiva", "High profitability"))
    elif nivel in ("low", "baja"):
        chips.append(("negativa", "Low profitability"))
    sequia = ind.get("sensibilidad_sequia")
    if sequia in ("high", "alta"):
        chips.append(("negativa", "Drought sensitive"))
    elif sequia in ("low", "baja"):
        chips.append(("positiva", "Drought tolerant"))
    if (ind.get("riesgo_hidrico") or {}).get("nivel") in ("high", "alto"):
        chips.append(("negativa", "High water risk"))

    return {
        "precio": ultimo,
        "precio_unidad": precio.get("unidad"),
        "variacion_pct": variacion,
        "rendimiento": rendimiento.get("p50"),
        "rendimiento_unidad": rendimiento.get("unidad"),
        "anio": ind.get("anio_ultimo"),
        "fuente": f"SIAP · {ubicacion['nombre']}",
        "etiquetas": [{"tipo": tipo, "texto": texto} for tipo, texto in chips],
    }


def fichas_de(activos: list[dict]) -> dict:
    """Fichas del catálogo de los cultivos en curso, por id del catálogo (para las alertas por cultivo)."""
    por_id = _catalogo()["por_id"]
    return {a["cultivo"]["catalogo_id"]: por_id[a["cultivo"]["catalogo_id"]]
            for a in activos if a["cultivo"].get("catalogo_id") in por_id}


def ficha_del_catalogo(catalogo_id: str) -> dict:
    """Ficha cruda del catálogo (la que usan los cálculos); NoEncontrado si el id no existe."""
    datos = _catalogo()["por_id"].get(catalogo_id)
    if datos is None:
        raise NoEncontrado(f"The catalog has no crop \"{catalogo_id}\"")
    return datos


def _ficha_inifap(f: dict) -> dict:
    """Una ficha de la Agenda Técnica del INIFAP, con las llaves en camelCase para el frontend."""
    return {
        "modalidad": f.get("modalidad"), "ciclo": f.get("ciclo"), "region": f.get("region"),
        "siembra": f.get("siembra"), "variedades": f.get("variedades") or [], "densidad": f.get("densidad"),
        "fertilizacion": f.get("fertilizacion"), "riego": f.get("riego"), "plagas": f.get("plagas") or [],
        "enfermedades": f.get("enfermedades") or [], "malezas": f.get("malezas"), "cosecha": f.get("cosecha"),
        "cuidados": f.get("cuidados") or [], "cita": f.get("cita"), "revisado": bool(f.get("revisado")),
        "costos": [
            {"modalidad": c.get("modalidad"), "costoTotalHa": c.get("costo_total_ha"), "rendimiento": c.get("rendimiento"),
             "unidadRendimiento": c.get("unidad_rendimiento"), "precio": c.get("precio")}
            for c in f.get("costos") or []
        ],
    }


def _manejo(datos: dict, cve_ent: str | None) -> dict:
    """Manejo del cultivo según las agendas del INIFAP del estado; pide el estado si no se conoce."""
    if not cve_ent:
        return {"necesitaEstado": True, "estado": None, "fuente": None, "nota": None, "fichas": []}
    m = catalogo_servicio.manejo(cve_ent, datos["id"], datos, None)
    hay_inifap = m.get("fuente") == "INIFAP"
    return {
        "necesitaEstado": False, "estado": estados.ESTADOS.get(cve_ent), "fuente": "INIFAP" if hay_inifap else None,
        "nota": m.get("nota"), "fichas": [_ficha_inifap(f) for f in m.get("fichas", [])] if hay_inifap else [],
    }


def estimaciones_economia(datos: dict, manejo: dict) -> list[dict]:
    """Cifras de partida para costos e ingresos: las tablas de costos del INIFAP del estado (costo por
    hectárea, rendimiento y precio) y la mediana nacional de SIAP. La persona las revisa y las ajusta."""
    opciones = []
    for f in manejo["fichas"]:
        for c in f["costos"]:
            if c["costoTotalHa"] is None:
                continue
            en_kg = c["unidadRendimiento"] == "kg/ha" and c["rendimiento"] is not None
            opciones.append({
                "fuente": f"INIFAP · {manejo['estado']}",
                "modalidad": c["modalidad"],
                "rendimientoTHa": round(c["rendimiento"] / 1000, 2) if en_kg else None,
                "precioT": round(c["precio"] * 1000) if en_kg and c["precio"] is not None else None,  # $/kg -> $/t
                "costoHa": c["costoTotalHa"],
            })
    nacional = datos.get("nacional") or {}
    if datos.get("unidad") in ("Tonelada", "Ton") and nacional.get("rend_p50") and nacional.get("pmr_real_p50"):
        opciones.append({
            "fuente": "SIAP national median", "modalidad": None, "rendimientoTHa": nacional["rend_p50"],
            "precioT": nacional["pmr_real_p50"], "costoHa": None,
        })
    return opciones


def ficha_por_catalogo(catalogo_id: str, cve_ent: str | None = None) -> dict | None:
    """Ficha completa de un cultivo del catálogo: condiciones, manejo del INIFAP (si se conoce el estado)
    y cifras sugeridas para costos e ingresos. None si el id no existe en el catálogo."""
    datos = _catalogo()["por_id"].get(catalogo_id)
    if datos is None:
        return None
    nacional = datos.get("nacional") or {}
    agua = datos.get("agua") or {}
    manejo = _manejo(datos, cve_ent)
    return {
        "catalogoId": datos["id"],
        "nombreCientifico": datos.get("cientifico"),
        "familia": datos.get("familia"),
        "fijaNitrogeno": bool(datos.get("fija_nitrogeno")),
        "descripcion": datos.get("descripcion"),
        "suelo": datos.get("suelo"),
        "cuidados": datos.get("cuidados") or [],
        "temperaturaOptimaC": datos.get("temperatura_optima_c"),
        "phOptimo": datos.get("ph_optimo"),
        "texturaIdeal": ecocrop.textura(datos.get("cientifico")),  # clases de EcoCrop; None si no trae
        "consumoAgua": agua.get("consumo"),
        "lluviaOptimaMm": agua.get("lluvia_optima_mm"),
        "cicloDias": datos.get("ciclo_dias"),
        "rendimientoNacionalTHa": nacional.get("rend_p50"),
        "textoRevisado": bool(datos.get("texto_revisado")),
        "fuentes": datos.get("fuentes") or [],
        "manejo": manejo,
        "estimaciones": estimaciones_economia(datos, manejo),
    }


def ficha(con, cultivo_id: int, cve_ent: str | None = None) -> dict | None:
    """Ficha del catálogo de un cultivo del Planificador; None si no viene del catálogo."""
    fila = _existe(con, "cultivo", cultivo_id, "crop")
    return ficha_por_catalogo(fila["catalogo_id"], cve_ent) if fila["catalogo_id"] else None
