"""Qué sembrar después en cada parcela (rotación de cultivos).

Con el catálogo de Cultivos la rotación mira dos cosas de lo último que se sembró:

- **Nitrógeno:** después de una leguminosa (fija nitrógeno) conviene un cereal que lo aproveche; después
  de un cereal, una hortaliza, una oleaginosa o un tubérculo conviene una leguminosa que lo reponga.
- **Familia botánica:** no se sugiere un cultivo de la misma familia, para cortar los ciclos de plagas y
  enfermedades que se quedan en el suelo.

Los candidatos salen de todo el catálogo (no solo de los cultivos que ya usa el Planificador): se
prefiere el que menos se ha sembrado en esa parcela y, si empatan, el de mayor superficie en México.
Si el último cultivo no viene del catálogo, o el catálogo no tiene candidatos, se usa la regla simple por
tipo (planificador.recomendar_por_tipo). No hay porcentaje de "afinidad": solo la razón.
"""

from datetime import date, timedelta

from app.db import clave
from app.services import catalogo_cultivos as catalogo
from app.services import planificador as plan_servicio
from app.services import tareas

# Tipos de cultivo que se rotan con esta regla (los perennes, forrajes e industriales no)
TIPOS_QUE_ROTAN = {"cereal", "leguminosa", "hortaliza", "oleaginosa", "tuberculo"}


def _fija_nitrogeno(ficha: dict, tipo: str) -> bool:
    """El catálogo trae la marca solo en los cultivos curados; en los demás se deduce del tipo."""
    marca = ficha.get("fija_nitrogeno")
    return bool(marca) if marca is not None else tipo == "leguminosa"


def _candidatos(buscar: str, ultimo: dict) -> list[dict]:
    resultado = []
    for c in catalogo._catalogo()["cultivos"]:
        if catalogo.tipo_del_planificador(c.get("tipo")) != buscar or c["id"] == ultimo["id"]:
            continue
        if c.get("perenne") or not c.get("ciclo_dias") or not c.get("ciclos_practicados"):
            continue  # solo cultivos anuales que se siembran en México
        if clave(c["nombre"]).startswith(("semilla", "seed")):
            continue
        if buscar == "leguminosa" and not c.get("fija_nitrogeno"):
            continue
        if ultimo.get("familia") and c.get("familia") == ultimo["familia"]:
            continue
        resultado.append(c)
    return resultado


def _desde_catalogo(con, parcela: dict, ultima: dict, hoy: date) -> dict | None:
    ficha = catalogo._catalogo()["por_id"].get(ultima["cultivo"].get("catalogo_id"))
    tipo = ultima["cultivo"]["tipo"]
    if ficha is None or tipo not in TIPOS_QUE_ROTAN:
        return None

    fija = _fija_nitrogeno(ficha, tipo)
    buscar = "cereal" if fija else "leguminosa"
    candidatos = _candidatos(buscar, ficha)
    if not candidatos:
        return None

    usadas = [s["cultivo"] for s in parcela["siembras"]]

    def usos(c: dict) -> int:
        return sum(1 for u in usadas if u.get("catalogo_id") == c["id"] or clave(u["nombre"]) == clave(c["nombre"]))

    def superficie(c: dict) -> float:
        return (c.get("nacional") or {}).get("superficie_sembrada_prom_ha") or 0

    elegido = min(candidatos, key=lambda c: (usos(c), -superficie(c), clave(c["nombre"])))

    local = con.execute("SELECT * FROM cultivo WHERE catalogo_id = ?", (elegido["id"],)).fetchone()
    sugerido = plan_servicio._cultivo_dict(local) if local else {
        "id": None, "nombre": elegido["nombre"], "tipo": catalogo.tipo_del_planificador(elegido.get("tipo")),
        "ciclo_dias": catalogo.ciclo_de(elegido), "catalogo_id": elegido["id"],
    }

    familia = ficha.get("familia")
    ultimo_nombre = ultima["cultivo"]["nombre"]
    cortar = f" It also rotates away from the {familia} family, which helps break pest and disease cycles." if familia else ""
    if buscar == "leguminosa":
        razon = f"Replenishes the nitrogen that {ultimo_nombre} used and improves the soil.{cortar}"
    else:
        razon = f"Makes use of the nitrogen that {ultimo_nombre} left.{cortar}"
    return {"sugerido": sugerido, "razon": razon}


def recomendaciones(con, plan: dict, hoy: date) -> list[dict]:
    catalogo_local = plan_servicio.listar_cultivos(con)
    resultado = []
    for p in plan["parcelas"]:
        if not p["siembras"]:
            continue
        ultima = max(p["siembras"], key=lambda s: s["fecha_cosecha"])
        elegida = _desde_catalogo(con, p, ultima, hoy) or plan_servicio.recomendar_por_tipo(catalogo_local, p, ultima)
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


def analisis(con, plan_id: int, hoy: date) -> dict:
    plan = plan_servicio.obtener_plan(con, plan_id)
    resumen = {**plan_servicio.resumen_plan(plan, hoy), **tareas.conteo_plan(con, plan_id, hoy)}
    return {"resumen": resumen, "recomendaciones": recomendaciones(con, plan, hoy)}
