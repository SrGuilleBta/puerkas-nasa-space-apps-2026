"""Tareas de una siembra (preparar, fertilizar, regar, cosechar...) con marca de hecha.

Cada tarea tiene una fecha; las que no están hechas y ya pasaron cuentan como vencidas. Se pueden
crear a mano o pedir un calendario sugerido, que es una plantilla general repartida a lo largo del
ciclo (no depende del cultivo): sirve de punto de partida y todo se puede editar.
"""

from datetime import date, timedelta

from app.services.planificador import Conflicto, Invalido, NoEncontrado, _existe, _fila

TIPOS = ("plant", "weed", "fertilize", "irrigate", "pests", "harvest", "other")

# Plantilla general: (tipo, título, parte del ciclo en que toca: 0 = siembra, 1 = cosecha)
PLANTILLA = [
    ("plant", "Planting day", 0.0),
    ("weed", "Weed control", 0.2),
    ("fertilize", "Fertilize", 0.3),
    ("pests", "Check for pests and disease", 0.5),
    ("irrigate", "Check irrigation and soil moisture", 0.65),
    ("harvest", "Harvest", 1.0),
]


def _dict(f) -> dict:
    return {
        "id": f["id"], "siembra_id": f["siembra_id"], "titulo": f["titulo"], "tipo": f["tipo"],
        "fecha": f["fecha"], "hecha": bool(f["hecha"]),
    }


def _validar(titulo: str, tipo: str) -> str:
    titulo = " ".join(titulo.split())
    if not titulo:
        raise Invalido("Enter a name for the task")
    if tipo not in TIPOS:
        raise Invalido(f"Unknown task type \"{tipo}\"")
    return titulo


def listar(con, siembra_id: int) -> list[dict]:
    _existe(con, "siembra", siembra_id, "planting")
    filas = con.execute("SELECT * FROM tarea WHERE siembra_id = ? ORDER BY fecha, id", (siembra_id,))
    return [_dict(f) for f in filas]


def crear(con, siembra_id: int, titulo: str, tipo: str, fecha: date) -> dict:
    _existe(con, "siembra", siembra_id, "planting")
    titulo = _validar(titulo, tipo)
    with con:
        id_ = con.execute(
            "INSERT INTO tarea (siembra_id, titulo, tipo, fecha) VALUES (?, ?, ?, ?)",
            (siembra_id, titulo, tipo, fecha.isoformat()),
        ).lastrowid
    return _dict(_existe(con, "tarea", id_, "task"))


def editar(con, tarea_id: int, cambios: dict) -> dict:
    """`cambios` trae solo lo que se quiere modificar (título, tipo, fecha, hecha)."""
    actual = _existe(con, "tarea", tarea_id, "task")
    titulo = _validar(cambios.get("titulo", actual["titulo"]), cambios.get("tipo", actual["tipo"]))
    fecha = cambios.get("fecha") or date.fromisoformat(actual["fecha"])
    hecha = int(cambios["hecha"]) if cambios.get("hecha") is not None else actual["hecha"]
    with con:
        con.execute(
            "UPDATE tarea SET titulo = ?, tipo = ?, fecha = ?, hecha = ? WHERE id = ?",
            (titulo, cambios.get("tipo", actual["tipo"]), fecha.isoformat(), hecha, tarea_id),
        )
    return _dict(_existe(con, "tarea", tarea_id, "task"))


def borrar(con, tarea_id: int) -> None:
    _existe(con, "tarea", tarea_id, "task")
    with con:
        con.execute("DELETE FROM tarea WHERE id = ?", (tarea_id,))


def sugeridas(con, siembra_id: int) -> list[dict]:
    """Crea el calendario sugerido de una siembra. Solo si todavía no tiene tareas, para no duplicar."""
    siembra = _existe(con, "siembra", siembra_id, "planting")
    if _fila(con, "SELECT 1 FROM tarea WHERE siembra_id = ? LIMIT 1", siembra_id):
        raise Conflicto("This planting already has tasks; delete them first to use the suggested schedule")
    inicio = date.fromisoformat(siembra["fecha_siembra"])
    dias = (date.fromisoformat(siembra["fecha_cosecha"]) - inicio).days
    with con:
        con.executemany(
            "INSERT INTO tarea (siembra_id, titulo, tipo, fecha) VALUES (?, ?, ?, ?)",
            [(siembra_id, titulo, tipo, (inicio + timedelta(days=round(dias * parte))).isoformat())
             for tipo, titulo, parte in PLANTILLA],
        )
    return listar(con, siembra_id)


def conteo_plan(con, plan_id: int, hoy: date) -> dict:
    """Tareas sin hacer de un plan y cuántas de ellas ya vencieron."""
    fila = con.execute(
        "SELECT COUNT(*) AS pendientes, COALESCE(SUM(t.fecha < ?), 0) AS vencidas FROM tarea t "
        "JOIN siembra s ON s.id = t.siembra_id JOIN parcela p ON p.id = s.parcela_id "
        "WHERE p.plan_id = ? AND t.hecha = 0",
        (hoy.isoformat(), plan_id),
    ).fetchone()
    return {"tareas_pendientes": fila["pendientes"], "tareas_vencidas": fila["vencidas"]}
