"""Une el Planificador con el catálogo de Cultivos (backend/pipeline/cultivos).

El Planificador guarda sus propios cultivos (tabla `cultivo`) para que las siembras no cambien si
cambia el catálogo. Cuando el usuario elige un cultivo del catálogo se crea (o se reutiliza) una fila
con `catalogo_id`, que sirve para mostrar la ficha (cuidados, temperatura, agua, suelo...).
"""

import unicodedata

from app.db import clave
from app.services import cultivos as catalogo_servicio
from app.services.planificador import NoEncontrado, _cultivo_dict, _existe, _fila

CICLO_PERENNE = 365  # un frutal o pasto perenne se planea por año


def _catalogo() -> dict:
    """El catálogo precalculado por la pipeline; vacío si todavía no se generó."""
    try:
        return catalogo_servicio.catalogo()
    except catalogo_servicio.SinDatos:
        return {"cultivos": [], "por_id": {}}


def tipo_del_planificador(tipo: str | None) -> str:
    """El catálogo escribe "Tubérculo"; el Planificador guarda el tipo en minúsculas y sin acentos
    (las reglas de rotación y de plagas dependen de esos valores)."""
    if not tipo:
        return "otro"
    sin_acentos = unicodedata.normalize("NFKD", tipo).encode("ascii", "ignore").decode()
    tipo = sin_acentos.strip().lower()
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


def ficha_del_catalogo(catalogo_id: str) -> dict:
    """Ficha cruda del catálogo (la que usan los cálculos); NoEncontrado si el id no existe."""
    datos = _catalogo()["por_id"].get(catalogo_id)
    if datos is None:
        raise NoEncontrado(f"The catalog has no crop \"{catalogo_id}\"")
    return datos


def ficha(con, cultivo_id: int) -> dict | None:
    """Ficha del catálogo de un cultivo del Planificador; None si no viene del catálogo."""
    fila = _existe(con, "cultivo", cultivo_id, "crop")
    datos = _catalogo()["por_id"].get(fila["catalogo_id"]) if fila["catalogo_id"] else None
    if datos is None:
        return None
    nacional = datos.get("nacional") or {}
    agua = datos.get("agua") or {}
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
        "consumoAgua": agua.get("consumo"),
        "lluviaOptimaMm": agua.get("lluvia_optima_mm"),
        "cicloDias": datos.get("ciclo_dias"),
        "rendimientoNacionalTHa": nacional.get("rend_p50"),
        "textoRevisado": bool(datos.get("texto_revisado")),
        "fuentes": datos.get("fuentes") or [],
    }
