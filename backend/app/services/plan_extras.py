"""Copiar un plan a otro año y exportarlo a CSV (se abre en Excel o Google Sheets)."""

import csv
import io
import re
from datetime import date

from app.db import clave
from app.services.planificador import Invalido, obtener_plan

MAX_ANIOS = 10


def _mover_anios(fecha: date, anios: int) -> date:
    """La misma fecha `anios` años después (el 29 de febrero pasa al 28 si el año no es bisiesto)."""
    try:
        return fecha.replace(year=fecha.year + anios)
    except ValueError:
        return fecha.replace(year=fecha.year + anios, day=28)


def duplicar_plan(con, plan_id: int, nombre: str | None, anios: int) -> dict:
    """Copia un plan (parcelas y siembras con sus datos económicos) moviendo las fechas `anios` años.

    Sirve para armar el plan del año siguiente a partir del actual. No copia las tareas: son del ciclo
    que ya pasó. El plan original no cambia.
    """
    if not 0 <= anios <= MAX_ANIOS:
        raise Invalido(f"The plan can be moved between 0 and {MAX_ANIOS} years")
    origen = obtener_plan(con, plan_id)
    nombre = " ".join((nombre or f"{origen['nombre']} (copy)").split())
    with con:  # una sola transacción: si algo falla no queda un plan a medias
        nuevo_id = con.execute("INSERT INTO plan (nombre) VALUES (?)", (nombre,)).lastrowid
        for p in origen["parcelas"]:
            parcela_id = con.execute(
                "INSERT INTO parcela (plan_id, nombre, clave, hectareas) VALUES (?, ?, ?, ?)",
                (nuevo_id, p["nombre"], clave(p["nombre"]), p["hectareas"]),
            ).lastrowid
            for s in p["siembras"]:
                con.execute(
                    "INSERT INTO siembra (parcela_id, cultivo_id, fecha_siembra, fecha_cosecha, hectareas,"
                    " rendimiento_t_ha, precio_t, costo_ha) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (parcela_id, s["cultivo"]["id"],
                     _mover_anios(date.fromisoformat(s["fecha_siembra"]), anios).isoformat(),
                     _mover_anios(date.fromisoformat(s["fecha_cosecha"]), anios).isoformat(),
                     s["hectareas"], s["rendimiento_t_ha"], s["precio_t"], s["costo_ha"]),
                )
    return {"id": nuevo_id, "nombre": nombre}


COLUMNAS = [
    "Plot", "Plot hectares", "Crop", "Type", "Planting date", "Harvest date", "Hectares planted",
    "Yield (t/ha)", "Price (MXN/t)", "Cost (MXN/ha)", "Estimated income (MXN)", "Estimated cost (MXN)",
    "Estimated profit (MXN)",
]


def _celda(valor):
    """Evita que Excel ejecute como fórmula un texto que empieza con = + - @ (lo escribe el usuario)."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return "" if valor is None else valor


def exportar_csv(con, plan_id: int) -> tuple[str, str]:
    """Devuelve (nombre de archivo, contenido CSV con BOM para que Excel lea bien los acentos)."""
    plan = obtener_plan(con, plan_id)
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS)
    for p in plan["parcelas"]:
        for s in p["siembras"]:
            escritor.writerow([_celda(v) for v in (
                p["nombre"], p["hectareas"], s["cultivo"]["nombre"], s["cultivo"]["tipo"],
                s["fecha_siembra"], s["fecha_cosecha"], s["hectareas"], s["rendimiento_t_ha"], s["precio_t"],
                s["costo_ha"], s["ingreso_estimado"], s["costo_total"], s["ganancia_estimada"],
            )])
    base = re.sub(r"[^a-z0-9]+", "-", clave(plan["nombre"])).strip("-") or "plan"
    return f"{base}.csv", "﻿" + salida.getvalue()
