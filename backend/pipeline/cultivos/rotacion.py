"""Rotación practicada: qué se siembra en el ciclo opuesto (O-I <-> P-V) en el mismo
municipio y año, combinado con reglas agronómicas (familia botánica y fijación de N).

SIAP no sigue parcelas, así que "rotación practicada" es una aproximación: que B se
siembre en el ciclo opuesto al de A, en el mismo municipio y año, en una superficie
comparable. En municipios grandes casi todo coexiste todos los años; por eso el
puntaje pondera por superficie y no solo por frecuencia.
"""

import numpy as np
import pandas as pd

from .indicadores import GEO

MIN_COOCURRENCIAS = 2
MIN_PRACTICA = 0.03   # por debajo, el socio es anecdótico en la zona
MAX_SOCIOS = 5
NOMBRE_CICLO = {"OI": "Fall-Winter", "PV": "Spring-Summer"}


def coocurrencia(agg: pd.DataFrame, desde: int) -> pd.DataFrame:
    a = agg[(agg["anio"] >= desde) & (agg["sembrada"] > 0) & agg["ciclo"].isin(["OI", "PV"])]
    pres = (a.groupby(["cvegeo", "cve_ent", "anio", "ciclo", "cultivo_id"], as_index=False)["sembrada"].sum())
    pv, oi = pres[pres["ciclo"] == "PV"], pres[pres["ciclo"] == "OI"]
    llave = ["cvegeo", "cve_ent", "anio"]
    cols = llave + ["ciclo", "cultivo_id"]
    ida = pv[cols].merge(oi[cols], on=llave, suffixes=("", "_socio"))
    vuelta = oi[cols].merge(pv[cols], on=llave, suffixes=("", "_socio"))
    pares = pd.concat([ida, vuelta], ignore_index=True)

    resultados = []
    for nivel, col in (("municipio", "cvegeo"), ("estado", "cve_ent"), ("nacional", None)):
        p = pares.assign(clave=pares[col] if col else "00", nivel=nivel)
        base = pres.assign(clave=pres[col] if col else "00", nivel=nivel)
        k_a = GEO + ["cultivo_id", "ciclo"]
        # Unidad de conteo: municipio-año (en nivel municipio equivale a años).
        por_ciclo = base.groupby(k_a).agg(n_cultivo=("anio", "size"), sem=("sembrada", "sum"))
        por_ciclo["peso"] = por_ciclo["sem"] / por_ciclo.groupby(level=GEO + ["cultivo_id"])["sem"].transform("sum")

        co = p.groupby(k_a + ["cultivo_id_socio", "ciclo_socio"]).size().rename("n_co").reset_index()
        co = co[co["n_co"] >= MIN_COOCURRENCIAS]
        co = co.join(por_ciclo, on=k_a)
        sem_socio = por_ciclo["sem"].rename("sem_socio")
        sem_socio.index = sem_socio.index.set_names(GEO + ["cultivo_id_socio", "ciclo_socio"])
        co = co.join(sem_socio, on=GEO + ["cultivo_id_socio", "ciclo_socio"])

        co["frecuencia"] = co["n_co"] / co["n_cultivo"]
        co["area_relativa"] = (co["sem_socio"] / co["sem"]).clip(upper=1.0)
        co["practica_ciclo"] = co["frecuencia"] * np.sqrt(co["area_relativa"])
        co["aporte"] = co["peso"] * co["practica_ciclo"]
        resultados.append(co)
    r = pd.concat(resultados, ignore_index=True)

    # Un cultivo en ambos ciclos suma el aporte de cada ciclo según su superficie;
    # la frecuencia y el ciclo del socio que se reportan son los del ciclo que más aporta.
    llave_par = GEO + ["cultivo_id", "cultivo_id_socio"]
    r = r.sort_values(llave_par + ["aporte", "ciclo_socio"], ascending=[True] * 4 + [False, True],
                      kind="mergesort")
    total = r.groupby(llave_par)["aporte"].sum().rename("practica")
    r = r.drop_duplicates(llave_par).join(total, on=llave_par)
    return r


def _agronomia(a: dict, b: dict, mismo: bool):
    if mismo:
        return 0.1, ["Monoculture: the same crop is repeated in both cycles"]
    puntos, razones = 0.5, []
    fa, fb = a.get("familia"), b.get("familia")
    if fa and fb:
        if fa == fb:
            puntos -= 0.35
            razones.append(f"Same family ({fa}): shares pests and diseases")
        else:
            puntos += 0.2
            razones.append("Different family: breaks pest cycles")
    if b.get("fija_nitrogeno") and not a.get("fija_nitrogeno"):
        puntos += 0.3
        razones.append("Legume: fixes nitrogen and reduces fertilizer needs")
    return max(0.0, min(1.0, puntos)), razones


def puntuar(co: pd.DataFrame, rasgos: dict, nombres: dict) -> pd.DataFrame:
    filas = []
    for r in co[co["practica"] >= MIN_PRACTICA].itertuples(index=False):
        a, b = rasgos.get(r.cultivo_id, {}), rasgos.get(r.cultivo_id_socio, {})
        agr, razones = _agronomia(a, b, r.cultivo_id == r.cultivo_id_socio)
        unidad = "years" if r.nivel == "municipio" else "municipality-years"
        razones.insert(0, f"Planted in the {NOMBRE_CICLO[r.ciclo_socio]} cycle in {r.frecuencia:.0%} of "
                          f"the {unidad} with this crop (area equivalent to {r.area_relativa:.0%})")
        filas.append({
            "nivel": r.nivel, "clave": r.clave, "cultivo_id": r.cultivo_id,
            "socio_id": r.cultivo_id_socio, "socio": nombres.get(r.cultivo_id_socio, r.cultivo_id_socio),
            "ciclo_socio": r.ciclo_socio,
            "practica": round(min(r.practica, 1.0), 2),
            "afinidad": round(0.5 * min(r.practica, 1.0) + 0.5 * agr, 2),
            "fija_nitrogeno": bool(b.get("fija_nitrogeno")),
            "razones": razones,
        })
    # Orden total (con desempates) para que la salida sea idéntica en cada corrida.
    df = pd.DataFrame(filas).sort_values(["afinidad", "practica", "socio_id"],
                                         ascending=[False, False, True], kind="mergesort")
    return df.groupby(GEO + ["cultivo_id"]).head(MAX_SOCIOS)
