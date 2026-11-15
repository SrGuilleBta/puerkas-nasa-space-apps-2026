"""Reglas del Planificador: planes, parcelas, siembras y catálogo de cultivos.

No conoce FastAPI: lanza errores propios que el router traduce a respuestas HTTP.
Regla principal: en una misma parcela dos siembras no pueden traslaparse en el tiempo.
El día de la cosecha pertenece a esa siembra; la siguiente puede empezar al día siguiente.
"""

import sqlite3
from datetime import date, timedelta

from app.db import clave


# ---------- Errores ----------
class ErrorPlanificador(Exception):
    def __init__(self, mensaje: str, **extra):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.extra = extra


class NoEncontrado(ErrorPlanificador):
    pass


class Invalido(ErrorPlanificador):
    pass


class Conflicto(ErrorPlanificador):
    pass


# ---------- Utilidades ----------
def _fila(con: sqlite3.Connection, sql: str, *args) -> sqlite3.Row | None:
    return con.execute(sql, args).fetchone()


def _existe(con, tabla: str, id_: int, que: str) -> sqlite3.Row:
    fila = _fila(con, f"SELECT * FROM {tabla} WHERE id = ?", id_)
    if fila is None:
        raise NoEncontrado(f"No {que} with id {id_}")
    return fila


def _cultivo_dict(f) -> dict:
    return {
        "id": f["id"], "nombre": f["nombre"], "tipo": f["tipo"], "ciclo_dias": f["ciclo_dias"],
        "catalogo_id": f["catalogo_id"],
    }


SIEMBRA_SQL = """
    SELECT s.id, s.parcela_id, s.fecha_siembra, s.fecha_cosecha, s.hectareas,
           s.rendimiento_t_ha, s.precio_t, s.costo_ha,
           c.id AS c_id, c.nombre AS c_nombre, c.tipo AS c_tipo, c.ciclo_dias AS c_ciclo,
           c.catalogo_id AS c_catalogo
    FROM siembra s JOIN cultivo c ON c.id = s.cultivo_id
"""


CAMPOS_ECONOMIA = ("rendimiento_t_ha", "precio_t", "costo_ha")


def _economia(f) -> dict:
    """Ingreso, costo y ganancia estimados de una siembra. Cada cifra solo sale si se capturaron los datos
    que necesita: ingreso = rendimiento x precio x hectáreas; costo = costo por hectárea x hectáreas."""
    ha = f["hectareas"]
    ingreso = None
    if f["rendimiento_t_ha"] is not None and f["precio_t"] is not None:
        ingreso = round(f["rendimiento_t_ha"] * f["precio_t"] * ha, 2)
    costo = round(f["costo_ha"] * ha, 2) if f["costo_ha"] is not None else None
    ganancia = round(ingreso - costo, 2) if ingreso is not None and costo is not None else None
    return {"ingreso_estimado": ingreso, "costo_total": costo, "ganancia_estimada": ganancia}


def _siembra_dict(f) -> dict:
    return {
        "id": f["id"],
        "parcela_id": f["parcela_id"],
        "fecha_siembra": f["fecha_siembra"],
        "fecha_cosecha": f["fecha_cosecha"],
        "hectareas": f["hectareas"],
        "rendimiento_t_ha": f["rendimiento_t_ha"],
        "precio_t": f["precio_t"],
        "costo_ha": f["costo_ha"],
        **_economia(f),
        "cultivo": {
            "id": f["c_id"], "nombre": f["c_nombre"], "tipo": f["c_tipo"], "ciclo_dias": f["c_ciclo"],
            "catalogo_id": f["c_catalogo"],
        },
    }


# ---------- Planes ----------
def listar_planes(con) -> list[dict]:
    return [dict(f) for f in con.execute("SELECT id, nombre FROM plan ORDER BY id")]


def obtener_plan(con, plan_id: int) -> dict:
    plan = _existe(con, "plan", plan_id, "plan")
    parcelas = [
        {"id": p["id"], "plan_id": p["plan_id"], "nombre": p["nombre"],
         "hectareas": p["hectareas"], "siembras": []}
        for p in con.execute("SELECT * FROM parcela WHERE plan_id = ? ORDER BY id", (plan_id,))
    ]
    por_id = {p["id"]: p for p in parcelas}
    if por_id:
        marcas = ",".join("?" * len(por_id))
        filas = con.execute(
            f"{SIEMBRA_SQL} WHERE s.parcela_id IN ({marcas}) ORDER BY s.fecha_siembra",
            tuple(por_id),
        )
        for f in filas:
            por_id[f["parcela_id"]]["siembras"].append(_siembra_dict(f))
    return {"id": plan["id"], "nombre": plan["nombre"], "parcelas": parcelas}


def crear_plan(con, nombre: str) -> dict:
    with con:
        id_ = con.execute("INSERT INTO plan (nombre) VALUES (?)", (nombre,)).lastrowid
    return {"id": id_, "nombre": nombre}


def renombrar_plan(con, plan_id: int, nombre: str) -> dict:
    _existe(con, "plan", plan_id, "plan")
    with con:
        con.execute("UPDATE plan SET nombre = ? WHERE id = ?", (nombre, plan_id))
    return {"id": plan_id, "nombre": nombre}


def borrar_plan(con, plan_id: int) -> None:
    _existe(con, "plan", plan_id, "plan")
    with con:
        con.execute("DELETE FROM plan WHERE id = ?", (plan_id,))


# ---------- Parcelas ----------
def _parcela_dict(f) -> dict:
    return {"id": f["id"], "plan_id": f["plan_id"], "nombre": f["nombre"],
            "hectareas": f["hectareas"], "siembras": []}


def _nombre_parcela_libre(con, plan_id: int, nombre: str, excepto_id: int | None = None) -> None:
    repetida = _fila(
        con, "SELECT nombre FROM parcela WHERE plan_id = ? AND clave = ? AND id IS NOT ?",
        plan_id, clave(nombre), excepto_id,
    )
    if repetida:
        raise Conflicto(f"A parcel named \"{repetida['nombre']}\" already exists in this plan")


def crear_parcela(con, plan_id: int, nombre: str, hectareas: float) -> dict:
    _existe(con, "plan", plan_id, "plan")
    _nombre_parcela_libre(con, plan_id, nombre)
    with con:
        id_ = con.execute(
            "INSERT INTO parcela (plan_id, nombre, clave, hectareas) VALUES (?, ?, ?, ?)",
            (plan_id, nombre, clave(nombre), hectareas),
        ).lastrowid
    return _parcela_dict(_existe(con, "parcela", id_, "parcel"))


def editar_parcela(con, parcela_id: int, nombre: str | None, hectareas: float | None) -> dict:
    actual = _existe(con, "parcela", parcela_id, "parcel")
    nombre = nombre if nombre is not None else actual["nombre"]
    hectareas = hectareas if hectareas is not None else actual["hectareas"]
    _nombre_parcela_libre(con, actual["plan_id"], nombre, excepto_id=parcela_id)
    mayor = _fila(con, "SELECT MAX(hectareas) AS m FROM siembra WHERE parcela_id = ?", parcela_id)["m"]
    if mayor is not None and hectareas < mayor:
        raise Conflicto(
            f"The parcel cannot be smaller than {mayor:g} ha: a planting already uses that area",
            hectareas_minimas=mayor,
        )
    with con:
        con.execute(
            "UPDATE parcela SET nombre = ?, clave = ?, hectareas = ? WHERE id = ?",
            (nombre, clave(nombre), hectareas, parcela_id),
        )
    return _parcela_dict(_existe(con, "parcela", parcela_id, "parcel"))


def borrar_parcela(con, parcela_id: int) -> None:
    _existe(con, "parcela", parcela_id, "parcel")
    with con:
        con.execute("DELETE FROM parcela WHERE id = ?", (parcela_id,))


# ---------- Catálogo de cultivos ----------
def listar_cultivos(con, q: str | None = None) -> list[dict]:
    filas = con.execute("SELECT * FROM cultivo ORDER BY nombre").fetchall()
    if q and q.strip():
        buscada = clave(q)
        filas = [f for f in filas if buscada in f["clave"]]  # sin acentos ni mayúsculas
    return [_cultivo_dict(f) for f in filas]


def crear_cultivo(con, nombre: str, tipo: str, ciclo_dias: int) -> dict:
    existente = _fila(con, "SELECT * FROM cultivo WHERE clave = ?", clave(nombre))
    if existente:
        raise Conflicto(
            f"The crop \"{existente['nombre']}\" already exists", cultivo=_cultivo_dict(existente)
        )
    with con:
        id_ = con.execute(
            "INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES (?, ?, ?, ?)",
            (nombre, clave(nombre), tipo.strip().lower(), ciclo_dias),
        ).lastrowid
    return _cultivo_dict(_existe(con, "cultivo", id_, "crop"))


# ---------- Siembras ----------
def _validar_siembra(con, parcela, cultivo_id, inicio: date, fin: date, hectareas: float,
                     excepto_id: int | None = None) -> None:
    if fin <= inicio:
        raise Invalido("Harvest must be after planting")
    if hectareas > parcela["hectareas"]:
        raise Invalido(
            f"The planting ({hectareas:g} ha) does not fit in the parcel ({parcela['hectareas']:g} ha)"
        )
    _existe(con, "cultivo", cultivo_id, "crop")

    # Traslape: los intervalos [siembra, cosecha] se tocan si cada uno empieza antes de que
    # termine el otro. El día de cosecha cuenta como ocupado.
    choque = _fila(
        con,
        f"{SIEMBRA_SQL} WHERE s.parcela_id = ? AND s.id IS NOT ? "
        "AND s.fecha_siembra <= ? AND s.fecha_cosecha >= ? ORDER BY s.fecha_siembra LIMIT 1",
        parcela["id"], excepto_id, fin.isoformat(), inicio.isoformat(),
    )
    if choque:
        libre = date.fromisoformat(choque["fecha_cosecha"]) + timedelta(days=1)
        raise Conflicto(
            f"Overlaps with {choque['c_nombre']} "
            f"({choque['fecha_siembra']} to {choque['fecha_cosecha']}) in this parcel; "
            f"it is free from {libre.isoformat()}",
            conflicto=_siembra_dict(choque),
            libre_desde=libre.isoformat(),
        )


def crear_siembra(con, parcela_id: int, cultivo_id: int, fecha_siembra: date,
                  fecha_cosecha: date | None, hectareas: float | None, economia: dict | None = None) -> dict:
    parcela = _existe(con, "parcela", parcela_id, "parcel")
    cultivo = _existe(con, "cultivo", cultivo_id, "crop")
    if fecha_cosecha is None:
        fecha_cosecha = fecha_siembra + timedelta(days=cultivo["ciclo_dias"])
    if hectareas is None:
        hectareas = parcela["hectareas"]
    _validar_siembra(con, parcela, cultivo_id, fecha_siembra, fecha_cosecha, hectareas)
    economia = economia or {}
    with con:
        id_ = con.execute(
            "INSERT INTO siembra (parcela_id, cultivo_id, fecha_siembra, fecha_cosecha, hectareas,"
            " rendimiento_t_ha, precio_t, costo_ha) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (parcela_id, cultivo_id, fecha_siembra.isoformat(), fecha_cosecha.isoformat(), hectareas,
             *(economia.get(k) for k in CAMPOS_ECONOMIA)),
        ).lastrowid
    return obtener_siembra(con, id_)


def obtener_siembra(con, siembra_id: int) -> dict:
    fila = _fila(con, f"{SIEMBRA_SQL} WHERE s.id = ?", siembra_id)
    if fila is None:
        raise NoEncontrado(f"No planting with id {siembra_id}")
    return _siembra_dict(fila)


def editar_siembra(con, siembra_id: int, cambios: dict) -> dict:
    """`cambios` trae solo los campos que se quieren modificar."""
    actual = _existe(con, "siembra", siembra_id, "planting")
    parcela = _existe(con, "parcela", actual["parcela_id"], "parcel")
    cultivo_id = cambios.get("cultivo_id") or actual["cultivo_id"]
    inicio = cambios.get("fecha_siembra") or date.fromisoformat(actual["fecha_siembra"])
    fin = cambios.get("fecha_cosecha") or date.fromisoformat(actual["fecha_cosecha"])
    hectareas = cambios.get("hectareas") or actual["hectareas"]
    _validar_siembra(con, parcela, cultivo_id, inicio, fin, hectareas, excepto_id=siembra_id)
    # Los datos económicos se pueden borrar (mandar null): se distingue "no vino" de "vino vacío"
    economia = [cambios[k] if k in cambios else actual[k] for k in CAMPOS_ECONOMIA]
    with con:
        con.execute(
            "UPDATE siembra SET cultivo_id = ?, fecha_siembra = ?, fecha_cosecha = ?, hectareas = ?,"
            " rendimiento_t_ha = ?, precio_t = ?, costo_ha = ? WHERE id = ?",
            (cultivo_id, inicio.isoformat(), fin.isoformat(), hectareas, *economia, siembra_id),
        )
    return obtener_siembra(con, siembra_id)


def borrar_siembra(con, siembra_id: int) -> None:
    _existe(con, "siembra", siembra_id, "planting")
    with con:
        con.execute("DELETE FROM siembra WHERE id = ?", (siembra_id,))


# ---------- Para Principal ----------
ETAPAS = 5  # el ciclo se divide en 5 etapas iguales ("etapa 3 de 5")


def siembras_en_curso(con, plan_id: int | None, hoy: date) -> list[dict]:
    """Siembras de un plan que están en curso en la fecha `hoy`, la que cosecha primero va primero.

    Sin `plan_id` usa el primer plan. `dia` cuenta desde 1 (el día de la siembra) y `etapa` divide
    el ciclo en 5 partes iguales. Más adelante aquí se pueden sumar precio y rentabilidad.
    """
    if plan_id is None:
        primero = _fila(con, "SELECT id FROM plan ORDER BY id LIMIT 1")
        if primero is None:
            return []
        plan_id = primero["id"]
    else:
        _existe(con, "plan", plan_id, "plan")

    filas = con.execute(
        f"{SIEMBRA_SQL} JOIN parcela p ON p.id = s.parcela_id "
        "WHERE p.plan_id = ? AND s.fecha_siembra <= ? AND s.fecha_cosecha >= ? "
        "ORDER BY s.fecha_cosecha, s.fecha_siembra, s.id",
        (plan_id, hoy.isoformat(), hoy.isoformat()),
    ).fetchall()

    resultado = []
    for f in filas:
        inicio = date.fromisoformat(f["fecha_siembra"])
        fin = date.fromisoformat(f["fecha_cosecha"])
        dias_totales = (fin - inicio).days + 1
        dia = (hoy - inicio).days + 1
        siembra = _siembra_dict(f)
        siembra.update(
            parcela=_parcela_resumen(con, f["parcela_id"]),
            dia=dia,
            dias_totales=dias_totales,
            avance=round(dia / dias_totales * 100),
            etapa=min(ETAPAS, (dia - 1) * ETAPAS // dias_totales + 1),
            etapas=ETAPAS,
        )
        resultado.append(siembra)
    return resultado


def _parcela_resumen(con, parcela_id: int) -> dict:
    p = _existe(con, "parcela", parcela_id, "parcel")
    return {"id": p["id"], "nombre": p["nombre"]}


# ---------- Resumen del ciclo y recomendaciones ----------
# Rotación simple por tipo de cultivo: después de un cereal conviene una leguminosa (repone
# nitrógeno) y después de una leguminosa, un cereal (lo aprovecha). Los demás tipos no tienen regla.
REGLAS_ROTACION = {
    "cereal": ("leguminosa", "Replenishes the nitrogen the cereal left and improves the soil."),
    "leguminosa": ("cereal", "Makes use of the nitrogen the legume left."),
}


def resumen_plan(plan: dict, hoy: date) -> dict:
    """Números del plan: siembras, cultivos distintos, uso del suelo hoy y próxima cosecha."""
    pares = [(p, s) for p in plan["parcelas"] for s in p["siembras"]]
    en_curso = [
        (p, s) for p, s in pares
        if date.fromisoformat(s["fecha_siembra"]) <= hoy <= date.fromisoformat(s["fecha_cosecha"])
    ]
    ha_totales = sum(p["hectareas"] for p in plan["parcelas"])
    ha_en_uso = sum(s["hectareas"] for _, s in en_curso)

    proximas = [(date.fromisoformat(s["fecha_cosecha"]), p, s) for p, s in pares
                if date.fromisoformat(s["fecha_cosecha"]) >= hoy]
    proxima = None
    if proximas:
        fecha, p, s = min(proximas, key=lambda t: t[0])
        proxima = {
            "fecha": fecha.isoformat(),
            "dias_restantes": (fecha - hoy).days,
            "cultivo": s["cultivo"]["nombre"],
            "parcela": p["nombre"],
        }
    con_ingreso = [s["ingreso_estimado"] for _, s in pares if s["ingreso_estimado"] is not None]
    con_costo = [s["costo_total"] for _, s in pares if s["costo_total"] is not None]
    con_ganancia = [s["ganancia_estimada"] for _, s in pares if s["ganancia_estimada"] is not None]
    return {
        "inversion_estimada": round(sum(con_costo), 2) if con_costo else None,
        "ingreso_estimado": round(sum(con_ingreso), 2) if con_ingreso else None,
        "ganancia_estimada": round(sum(con_ganancia), 2) if con_ganancia else None,
        "siembras_con_economia": sum(
            1 for _, s in pares if s["ingreso_estimado"] is not None or s["costo_total"] is not None
        ),
        "total_siembras": len(pares),
        "cultivos_distintos": len({s["cultivo"]["id"] for _, s in pares}),
        "en_curso": len(en_curso),
        "hectareas_totales": ha_totales,
        "hectareas_en_uso": ha_en_uso,
        "uso_suelo": round(ha_en_uso / ha_totales * 100) if ha_totales else 0,
        "proxima_cosecha": proxima,
    }


def recomendar_por_tipo(catalogo: list[dict], parcela: dict, ultima: dict) -> dict | None:
    """Regla simple por tipo (cereal <-> leguminosa) con los cultivos que ya tiene el Planificador.
    Es el respaldo cuando el último cultivo no viene del catálogo de Cultivos."""
    regla = REGLAS_ROTACION.get(ultima["cultivo"]["tipo"])
    if regla is None:
        return None
    tipo_siguiente, razon = regla
    candidatos = [c for c in catalogo if c["tipo"] == tipo_siguiente and c["id"] != ultima["cultivo"]["id"]]
    if not candidatos:
        return None
    usos = {c["id"]: sum(1 for s in parcela["siembras"] if s["cultivo"]["id"] == c["id"]) for c in candidatos}
    return {"sugerido": min(candidatos, key=lambda c: (usos[c["id"]], c["nombre"])), "razon": razon}


def recomendaciones_plan(con, plan: dict, hoy: date) -> list[dict]:
    """Qué sembrar después en cada parcela, según la última siembra y la regla de rotación.

    Entre varios candidatos del tipo recomendado se prefiere el que menos se ha sembrado en esa
    parcela (para variar) y, si empatan, el primero por nombre. Nunca se sugiere repetir el mismo
    cultivo. No hay porcentaje de "afinidad": solo la razón de la regla.
    """
    catalogo = listar_cultivos(con)
    resultado = []
    for p in plan["parcelas"]:
        if not p["siembras"]:
            continue
        ultima = max(p["siembras"], key=lambda s: s["fecha_cosecha"])
        elegida = recomendar_por_tipo(catalogo, p, ultima)
        if elegida is None:
            continue
        desde = max(hoy, date.fromisoformat(ultima["fecha_cosecha"]) + timedelta(days=1))
        resultado.append({
            "parcela": {"id": p["id"], "nombre": p["nombre"]},
            "despues_de": {"cultivo": ultima["cultivo"], "fecha_cosecha": ultima["fecha_cosecha"]},
            "sugerido": elegida["sugerido"],
            "desde": desde.isoformat(),
            "razon": elegida["razon"],
        })
    return resultado


def analisis_plan(con, plan_id: int, hoy: date) -> dict:
    plan = obtener_plan(con, plan_id)
    return {"resumen": resumen_plan(plan, hoy), "recomendaciones": recomendaciones_plan(con, plan, hoy)}
