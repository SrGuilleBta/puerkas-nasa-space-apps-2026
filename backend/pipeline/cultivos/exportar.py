"""Escribe los JSON que lee la API: catálogo, ubicaciones y un archivo por ubicación."""

import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd

from . import config
from .indicadores import riesgo_hidrico, sensibilidad_sequia


def _r(v, n=2):
    if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
        return None
    return round(float(v), n)


def _limpio(d):
    """Quita llaves con None para que los archivos pesen menos."""
    if isinstance(d, dict):
        return {k: _limpio(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_limpio(v) for v in d]
    return d


def _escribir(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(_limpio(datos), f, ensure_ascii=False, separators=(",", ":"))


def _agrupar(df, llaves):
    cubetas = defaultdict(list)
    for rec in df.to_dict("records"):
        cubetas[tuple(rec[k] for k in llaves)].append(rec)
    return cubetas


# ---------------------------------------------------------------- Etiquetas

def _etiquetas(c, ficha, rot, sens, riesgo):
    et = []
    pctl = c["pctl_ingreso"]
    if not pd.isna(pctl):
        if pctl >= 0.75:
            et.append(("positiva", "Alta rentabilidad",
                       "Ingreso por hectárea sembrada entre el 25% más alto de la zona"))
        elif pctl <= 0.25:
            et.append(("negativa", "Rentabilidad baja",
                       "Ingreso por hectárea sembrada entre el 25% más bajo de la zona"))
    if rot:
        mejor = rot[0]
        if mejor["afinidad"] >= 0.6 and mejor["socio_id"] != c["cultivo_id"]:
            extra = " (leguminosa)" if mejor["fija_nitrogeno"] else ""
            et.append(("positiva", "Rotación favorable", f"Compatible con {mejor['socio'].lower()}{extra}"))
    if sens == "alta":
        et.append(("negativa", "Sensible a sequía",
                   f"El siniestro sube de {c['tasa_siniestro_normal']:.0%} a "
                   f"{c['tasa_siniestro_sequia']:.0%} en temporadas de sequía severa"))
    elif sens == "baja" and c["pct_riego"] < 0.5:
        et.append(("positiva", "Tolera la sequía",
                   "El siniestro casi no cambia en temporadas de sequía severa"))
    if riesgo == "alto":
        et.append(("negativa", "Riesgo hídrico alto", "Depende de la lluvia y su rendimiento varía mucho"))
    elif riesgo == "bajo" and c["pct_riego"] >= 0.7:
        et.append(("positiva", "Mayormente de riego", f"{c['pct_riego']:.0%} de la superficie es de riego"))
    if ficha.get("tolerancia_encharcamiento") == "sensible" and len(et) < 3:
        et.append(("negativa", "Sensible a encharcamiento", "Requiere suelo con buen drenaje (EcoCrop)"))
    return [{"tipo": t, "titulo": a, "detalle": b} for t, a, b in et]


def _situacion(c, ctx, desde):
    s = []
    ult, prev = c["pmr_real_ultimo"], c["pmr_real_p50_previo"]
    if not pd.isna(ult) and not pd.isna(prev) and prev > 0:
        delta = ult / prev - 1
        periodo = f"{desde}–{int(c['anio_ultimo']) - 1}"
        if delta >= 0.05:
            s.append(("positiva", "Precio por encima del promedio",
                      f"El precio medio rural de {int(c['anio_ultimo'])} fue {delta:.0%} mayor "
                      f"que la mediana {periodo} (pesos de {config.ANIO_BASE_PRECIOS})"))
        elif delta <= -0.05:
            s.append(("alerta", "Precio por debajo del promedio",
                      f"El precio medio rural de {int(c['anio_ultimo'])} fue {abs(delta):.0%} menor "
                      f"que la mediana {periodo} (pesos de {config.ANIO_BASE_PRECIOS})"))
    if ctx and c["pct_riego"] < 0.5:
        cat = ctx.get("cat_actual_max")
        if cat is not None and cat >= 1:
            if ctx["nivel"] == "municipio":
                det = f"Monitor de Sequía al {ctx['fecha_actual']}: D{int(cat)} en el municipio."
            else:
                det = (f"Monitor de Sequía al {ctx['fecha_actual']}: {ctx['pct_mun_en_sequia']:.0%} "
                       f"de los municipios con sequía (hasta D{int(cat)}).")
            det += f" El {1 - c['pct_riego']:.0%} de este cultivo aquí es de temporal."
            s.append(("alerta", "Riesgo hídrico próximo", det))
    return [{"tipo": t, "titulo": a, "detalle": b} for t, a, b in s]


# ---------------------------------------------------------------- Entradas

def _combo(r):
    return {
        "ciclo": r["ciclo"], "modalidad": r["modalidad"], "n_anios": int(r["n_anios"]),
        "superficie_sembrada_prom_ha": _r(r["sembrada_prom_ha"], 1),
        "rend_p25": _r(r["rend_p25"]), "rend_p50": _r(r["rend_p50"]), "rend_p75": _r(r["rend_p75"]),
        "cv_rendimiento": _r(r["cv_rendimiento"]),
        "pmr_real_p50": _r(r["pmr_real_p50"], 0),
        "tasa_siniestro": _r(r["tasa_siniestro"], 3),
    }


def _entrada(c, ficha, combos, rot, rot_nivel, ctx, desde):
    unidad = ficha.get("unidad", "Tonelada")
    u_rend = "t/ha" if unidad == "Tonelada" else f"{unidad}/ha"
    u_precio = "$/t" if unidad == "Tonelada" else f"$/{unidad}"
    sens = sensibilidad_sequia(c["tasa_siniestro_sequia"], c["tasa_siniestro_normal"],
                               c["n_temporadas_sequia"], c["n_temporadas_normales"])
    score, riesgo = riesgo_hidrico(c["pct_riego"], c["cv_rendimiento_temporal"],
                                   (ctx or {}).get("frec_d2"))
    pctl = c["pctl_ingreso"]
    renta = None if pd.isna(pctl) else ("alta" if pctl >= 0.75 else "baja" if pctl <= 0.25 else "media")
    reparto = {k: _r(c[f"pct_{k}"]) for k in ("OI", "PV", "PER") if c[f"pct_{k}"] > 0}
    principal = max(reparto, key=reparto.get) if reparto else None

    return {
        "id": c["cultivo_id"],
        "nombre": ficha.get("nombre"),
        "n_anios": int(c["n_anios"]),
        "anio_ultimo": int(c["anio_ultimo"]),
        "superficie_sembrada_prom_ha": _r(c["sembrada_prom_ha"], 1),
        "rendimiento": {
            "p25": _r(c["rend_p25"]), "p50": _r(c["rend_p50"]), "p75": _r(c["rend_p75"]),
            "cv": _r(c["cv_rendimiento"]), "unidad": u_rend,
        },
        "precio": {
            "pmr_real_p50": _r(c["pmr_real_p50"], 0),
            "pmr_real_ultimo": _r(c["pmr_real_ultimo"], 0),
            "pmr_nominal_ultimo": _r(c["pmr_nominal_ultimo"], 0),
            "unidad": u_precio, "anio_base": config.ANIO_BASE_PRECIOS,
        },
        "rentabilidad": {
            "ingreso_ha_real_p50": _r(c["ingreso_ha_real_p50"], 0),
            "percentil_zona": _r(pctl), "nivel": renta,
        },
        "siniestro": {
            "tasa": _r(c["tasa_siniestro"], 3),
            "tasa_sequia": _r(c["tasa_siniestro_sequia"], 3),
            "tasa_normal": _r(c["tasa_siniestro_normal"], 3),
            "n_temporadas_sequia": int(c["n_temporadas_sequia"]),
            "n_temporadas_normales": int(c["n_temporadas_normales"]),
        },
        "sensibilidad_sequia": sens,
        "riesgo_hidrico": {
            "score": score, "nivel": riesgo, "pct_riego": _r(c["pct_riego"]),
            "cv_rendimiento_temporal": _r(c["cv_rendimiento_temporal"]),
        },
        "ciclos": reparto,
        "ciclo_principal": principal,
        "por_ciclo_modalidad": [_combo(r) for r in sorted(combos, key=lambda r: -r["sembrada_prom_ha"])],
        "rotacion": None if principal == "PER" else {
            "nivel_datos": rot_nivel,
            "socios": [{k: s[k] for k in ("socio_id", "socio", "ciclo_socio", "practica", "afinidad",
                                           "fija_nitrogeno", "razones")} for s in rot],
        },
        "etiquetas": _etiquetas(c, ficha, rot, sens, riesgo),
        "situacion_actual": _situacion(c, ctx, desde),
        "gaez": {"score_idoneidad": None, "brecha_rendimiento": None, "estado": "pendiente"},
    }


def exportar(catalogo, por_cult, por_combo, rot, ctx_seq, nombres_geo, desde, hasta, fuentes_meta):
    salida = config.SALIDA_DIR
    for sub in ("municipios", "estados"):
        if (salida / sub).exists():
            shutil.rmtree(salida / sub)

    fichas = {e["id"]: e for e in catalogo}
    combos = _agrupar(por_combo, ["nivel", "clave", "cultivo_id"])
    rots = _agrupar(rot, ["nivel", "clave", "cultivo_id"])
    ctxs = {(r["nivel"], r["clave"]): r for r in ctx_seq.to_dict("records")}
    estados, municipios = nombres_geo

    n = 0
    for (nivel, clave), grupo in por_cult.groupby(["nivel", "clave"]):
        ctx = ctxs.get((nivel, clave))
        cultivos = []
        for c in grupo.sort_values("sembrada_prom_ha", ascending=False).to_dict("records"):
            cid = c["cultivo_id"]
            if cid not in fichas:
                continue
            r, r_nivel = rots.get((nivel, clave, cid), []), nivel
            if not r and nivel == "municipio":  # sin rotación local: usar la del estado
                r, r_nivel = rots.get(("estado", clave[:2], cid), []), "estado"
            cultivos.append(_entrada(c, fichas[cid], combos.get((nivel, clave, cid), []),
                                     r, r_nivel if r else None, ctx, desde))

        if nivel == "municipio":
            ubic = {"nivel": nivel, "clave": clave, "nombre": municipios.get(clave),
                    "cve_ent": clave[:2], "estado": estados.get(clave[:2])}
            ruta = salida / "municipios" / f"{clave}.json"
        elif nivel == "estado":
            ubic = {"nivel": nivel, "clave": clave, "nombre": estados.get(clave)}
            ruta = salida / "estados" / f"{clave}.json"
        else:
            ubic = {"nivel": nivel, "clave": "00", "nombre": "México"}
            ruta = salida / "nacional.json"

        sup = float(grupo["sembrada_prom_ha"].sum())
        riego = float((grupo["sembrada_prom_ha"] * grupo["pct_riego"].fillna(0)).sum())
        contexto = {
            "superficie_sembrada_prom_ha": round(sup, 1),
            "pct_riego": round(riego / sup, 2) if sup else None,
            "n_cultivos": len(cultivos),
            "sequia": None if not ctx else {
                "frec_d1": _r(ctx["frec_d1"]), "frec_d2": _r(ctx["frec_d2"]),
                "categoria_actual": None if pd.isna(ctx["cat_actual_max"]) else int(ctx["cat_actual_max"]),
                "pct_municipios_en_sequia": _r(ctx["pct_mun_en_sequia"]),
                "fecha": ctx["fecha_actual"],
            },
        }
        _escribir(ruta, {"ubicacion": ubic, "ventana": [desde, hasta], "contexto": contexto,
                         "cultivos": cultivos})
        n += 1

    _escribir(salida / "catalogo.json", {"ventana": [desde, hasta], "cultivos": catalogo})
    _escribir(salida / "meta.json", {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ventana": [desde, hasta], "anio_base_precios": config.ANIO_BASE_PRECIOS,
        "fuentes": fuentes_meta,
    })
    return n


def exportar_ubicaciones(estados, municipios_siap, nombres_sequia, con_datos):
    """Lista para el selector: todos los municipios INEGI (vía Monitor) + los de SIAP."""
    claves = set(municipios_siap) | set(nombres_sequia)
    por_estado = defaultdict(list)
    for cve in sorted(claves):
        nombre = (nombres_sequia.get(cve) or {}).get("NOMBRE_MUN") or municipios_siap.get(cve)
        por_estado[cve[:2]].append({"clave": cve, "nombre": nombre, "con_datos": cve in con_datos})
    lista = [{"clave": e, "nombre": estados.get(e), "municipios": sorted(m, key=lambda x: x["nombre"] or "")}
             for e, m in sorted(por_estado.items()) if e in estados]
    _escribir(config.SALIDA_DIR / "ubicaciones.json", {"estados": lista})
