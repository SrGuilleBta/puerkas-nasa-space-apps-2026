"""Lee los JSON precalculados por la pipeline (backend/pipeline/cultivos).

No calcula nada: solo carga archivos y junta la ficha del catálogo con los
indicadores de la ubicación. Si falta un dato en el municipio, cae al estado y
luego al nivel nacional.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATOS = Path(__file__).resolve().parents[2] / "data" / "cultivos"


def _normal(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


class SinDatos(Exception):
    """La pipeline no se ha corrido o la clave no existe."""


def _leer(ruta: Path) -> dict:
    if not ruta.exists():
        raise SinDatos(str(ruta.relative_to(DATOS.parent)))
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def catalogo() -> dict:
    datos = _leer(DATOS / "catalogo.json")
    datos["por_id"] = {c["id"]: c for c in datos["cultivos"]}
    return datos


@lru_cache(maxsize=1)
def ubicaciones() -> dict:
    return _leer(DATOS / "ubicaciones.json")


@lru_cache(maxsize=1)
def _indice_ubicaciones() -> dict:
    """clave -> descriptor de ubicación, para todas las claves válidas (con o sin datos)."""
    idx = {"00": {"nivel": "national", "clave": "00", "nombre": "Mexico"}}
    for e in ubicaciones()["estados"]:
        idx[e["clave"]] = {"nivel": "state", "clave": e["clave"], "nombre": e["nombre"]}
        for m in e["municipios"]:
            idx[m["clave"]] = {"nivel": "municipality", "clave": m["clave"], "nombre": m["nombre"],
                               "cve_ent": e["clave"], "estado": e["nombre"]}
    return idx


@lru_cache(maxsize=1)
def meta() -> dict:
    return _leer(DATOS / "meta.json")


@lru_cache(maxsize=512)
def ubicacion(clave: str) -> dict:
    """clave: '00' (nacional), 2 dígitos (estado) o 5 dígitos (municipio, CVEGEO)."""
    if clave == "00":
        return _leer(DATOS / "nacional.json")
    if len(clave) == 2:
        return _leer(DATOS / "estados" / f"{clave}.json")
    if len(clave) == 5:
        return _leer(DATOS / "municipios" / f"{clave}.json")
    raise SinDatos(clave)


def _buscar(clave: str, cultivo: str):
    try:
        datos = ubicacion(clave)
    except SinDatos:
        return None, None
    for c in datos["cultivos"]:
        if c["id"] == cultivo:
            return datos, c
    return datos, None


def indicadores_de(cultivo: str, claves: list[str]) -> tuple[dict | None, dict | None]:
    """Indicadores de SIAP de un cultivo (precio, rendimiento, rentabilidad...) en la primera ubicación
    de `claves` donde se siembra, junto con el descriptor de esa ubicación. (None, None) si en ninguna."""
    for clave in claves:
        datos, ind = _buscar(clave, cultivo)
        if ind is not None:
            return ind, datos["ubicacion"]
    return None, None


def viabilidad(clave: str, cultivo: str) -> dict:
    """Ficha completa de un cultivo en una ubicación.

    `nivel_datos` indica de dónde salieron los indicadores: si el municipio no
    siembra el cultivo, se devuelven los del estado (o los nacionales) y
    `sembrado_en_ubicacion` es False.
    """
    ficha = catalogo()["por_id"].get(cultivo)
    if ficha is None:
        raise SinDatos(f"crop {cultivo}")
    descriptor = _indice_ubicaciones().get(clave)
    if descriptor is None:
        raise SinDatos(f"location {clave}")

    cadena = [clave]
    if len(clave) == 5:
        cadena.append(clave[:2])
    if clave != "00":
        cadena.append("00")

    # Un municipio sin registros agrícolas en SIAP (p. ej. Monterrey) no tiene archivo:
    # se responde igual, con contexto vacío y los indicadores del estado.
    pedida, _ = _buscar(clave, cultivo)
    indicadores, origen = None, None
    for k in cadena:
        datos, ind = _buscar(k, cultivo)
        if ind is not None:
            indicadores, origen = ind, datos["ubicacion"]
            break

    enchar = ficha.get("tolerancia_encharcamiento")
    cve_ent = descriptor.get("cve_ent") or (clave if descriptor["nivel"] == "state" else None)
    pct_riego = ((indicadores or {}).get("riesgo_hidrico") or {}).get("pct_riego")
    return {
        "ubicacion": descriptor,
        "contexto": pedida["contexto"] if pedida else None,
        "ventana": catalogo()["ventana"],
        "ficha": {k: v for k, v in ficha.items() if k != "nacional"},
        "nacional": ficha.get("nacional"),
        "sembrado_en_ubicacion": origen is not None and origen["clave"] == clave,
        "nivel_datos": origen["nivel"] if origen else None,
        "ubicacion_datos": origen,
        "indicadores": indicadores,
        "sensibilidad_inundacion": {
            "nivel": {"tolerant": "low", "sensitive": "high"}.get(enchar),
            "fuente": "EcoCrop (tolerance to poor drainage)",
            "pendiente": "National Risk Atlas (CENAPRED)",
        },
        "manejo": manejo(cve_ent, cultivo, ficha, pct_riego),
    }


# ---------------------------------------------------------------- Manejo INIFAP

CUIDADOS_DIR = DATOS.parent / "inifap" / "cuidados"
# Ciudad de México no tiene Agenda Técnica: se usa la del Estado de México.
ESTADO_SUSTITUTO = {"09": "15"}


@lru_cache(maxsize=1)
def _fichas_inifap() -> dict:
    """(cve_ent, cultivo_id) -> fichas de las Agendas Técnicas del INIFAP (un JSON por estado)."""
    idx = {}
    for ruta in sorted(CUIDADOS_DIR.glob("*.json")):
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        for fi in datos["fichas"]:
            fi = {**fi, "cita": datos["fuente"].rstrip(".") + f", pp. {fi['paginas'][0]}–{fi['paginas'][1]}."}
            for cid in fi["cultivo_ids"]:
                idx.setdefault((datos["cve_ent"], cid), []).append(fi)
    return idx


def manejo(cve_ent: str | None, cultivo: str, ficha: dict, pct_riego: float | None) -> dict:
    """Cuidados del cultivo: fichas INIFAP del estado si existen; si no, el texto general.

    Las fichas se ordenan poniendo primero la modalidad que domina en la zona
    (riego si al menos la mitad de la superficie es de riego).
    """
    sustituto = ESTADO_SUSTITUTO.get(cve_ent)
    fichas = list(_fichas_inifap().get((sustituto or cve_ent, cultivo), [])) if cve_ent else []
    if fichas:
        preferida = None if pct_riego is None else ("irrigated" if pct_riego >= 0.5 else "rainfed")
        fichas.sort(key=lambda f: f.get("modalidad") != preferida)
        return {
            "fuente": "INIFAP",
            "nota": "Mexico City has no INIFAP Technical Agenda; the State of Mexico agenda is used." if sustituto else None,
            "fichas": fichas,
            "siembra_meses": fichas[0]["siembra"]["meses"],
        }
    return {
        "fuente": "general" if ficha.get("cuidados") else None,
        "nota": "No INIFAP technical agenda for this state and crop; general draft text.",
        "cuidados": ficha.get("cuidados"),
        "fichas": [],
        "siembra_meses": None,
    }


def biblioteca(clave: str | None = None, buscar: str | None = None, tipo: str | None = None) -> list[dict]:
    """Lista ligera para la biblioteca del frontend.

    `buscar` se compara (sin acentos ni mayúsculas) con el nombre en inglés, el nombre SIAP en
    español, el nombre científico y el id. `tipo` filtra por tipo de cultivo (p. ej. "Cereal");
    "Other" trae los que no tienen tipo. Con `clave`, ordena por superficie en esa ubicación y
    marca qué cultivos se siembran ahí; sin ella, por superficie nacional.
    """
    cat = catalogo()["cultivos"]
    locales = {}
    if clave:
        if clave not in _indice_ubicaciones():
            raise SinDatos(f"location {clave}")
        try:
            locales = {c["id"]: c for c in ubicacion(clave)["cultivos"]}
        except SinDatos:
            pass  # municipio válido sin registros agrícolas: catálogo completo sin marcar
    q = _normal(buscar).strip() if buscar else ""

    # Duplicados: mismo nombre, mismo tipo y misma descripción (SIAP reporta algunos cultivos en dos
    # unidades, p. ej. fresa en toneladas y en plantas). Se muestra solo el más relevante: el que más
    # se siembra en la zona (o en el país si no hay zona). Si cambia alguno de los tres, son cultivos distintos.
    grupo = lambda c: (c["nombre"].strip().lower(), c.get("tipo") or "Other", c.get("descripcion") or "")
    relevancia = lambda c: ((locales[c["id"]]["superficie_sembrada_prom_ha"] if c["id"] in locales else 0),
                            c["nacional"]["superficie_sembrada_prom_ha"])
    representante: dict = {}
    for c in cat:
        g = grupo(c)
        if g not in representante or relevancia(c) > relevancia(representante[g]):
            representante[g] = c

    filas = []
    for c in cat:
        if representante[grupo(c)] is not c:
            continue
        if tipo and (c.get("tipo") or "Other") != tipo:
            continue
        if q:
            pajar = " ".join(_normal(t) for t in (c["nombre"], c.get("nombre_es") or "", c.get("cientifico") or "",
                                                  c["id"].replace("-", " ")))
            if q not in pajar:
                continue
        loc = locales.get(c["id"])
        filas.append({
            "id": c["id"], "nombre": c["nombre"], "nombre_es": c.get("nombre_es"),
            "cientifico": c.get("cientifico"), "tipo": c.get("tipo") or "Other",
            "ciclo_dias": c.get("ciclo_dias"), "perenne": c.get("perenne"),
            "unidad": c.get("unidad"),
            "sembrado_en_ubicacion": loc is not None,
            "superficie_local_ha": loc["superficie_sembrada_prom_ha"] if loc else None,
            "superficie_nacional_ha": c["nacional"]["superficie_sembrada_prom_ha"],
        })
    if clave:
        filas.sort(key=lambda f: -(f["superficie_local_ha"] or 0))
    return filas
