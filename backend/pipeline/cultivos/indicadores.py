"""Indicadores derivados de SIAP cruzados con el Monitor de Sequía.

Todo se calcula en tres niveles a la vez (municipio, estado, nacional) para que la
app pueda responder a cualquiera de los dos filtros y caer al nivel superior cuando
un municipio no tiene registros de un cultivo.
"""

import numpy as np
import pandas as pd

from . import config

SUMAS = ["sembrada", "cosechada", "siniestrada", "volumen", "valor", "valor_real",
         "sem_riego", "sem_seq", "sin_seq", "sem_norm", "sin_norm", "temp_seq", "temp_norm"]
GEO = ["nivel", "clave"]


def ventana(agg: pd.DataFrame) -> tuple[int, int]:
    fin = int(agg["anio"].max())
    return fin - config.VENTANA_ANIOS + 1, fin


def por_nivel(agg: pd.DataFrame) -> pd.DataFrame:
    """Repite las filas por municipio, estado y nación con columnas nivel/clave."""
    num = ["sembrada", "cosechada", "siniestrada", "volumen", "valor"]
    resto = ["anio", "cultivo_id", "ciclo", "modalidad"]
    mun = agg.assign(nivel="municipio", clave=agg["cvegeo"])
    est = (agg.groupby(["cve_ent"] + resto, as_index=False)[num].sum()
           .assign(nivel="estado").rename(columns={"cve_ent": "clave"}))
    nac = agg.groupby(resto, as_index=False)[num].sum().assign(nivel="nacional", clave="00")
    return pd.concat([d[GEO + resto + num] for d in (mun, est, nac)], ignore_index=True)


# ---------------------------------------------------------------- Sequía

def temporadas_sequia(seq: pd.DataFrame, anios: range) -> pd.DataFrame:
    """Marca cada (nivel, clave, año, ciclo) como temporada con sequía severa o no."""
    filas = []
    for anio in anios:
        for ciclo, ((d0, m0), (d1, m1)) in config.TEMPORADAS.items():
            ini = pd.Timestamp(anio + d0, m0, 1)
            fin = pd.Timestamp(anio + d1, m1, 1) + pd.offsets.MonthEnd(0)
            sub = seq[(seq["fecha"] >= ini) & (seq["fecha"] <= fin)]
            if sub.empty:
                continue
            frac = (sub["categoria"] >= 2).groupby(sub["cvegeo"]).mean()
            filas.append(pd.DataFrame({"cvegeo": frac.index, "anio": anio, "ciclo": ciclo,
                                       "severa": frac.values >= config.UMBRAL_LECTURAS_D2}))
    t = pd.concat(filas, ignore_index=True)
    t["cve_ent"] = t["cvegeo"].str[:2]

    mun = t.assign(nivel="municipio", clave=t["cvegeo"])
    est = (t.groupby(["cve_ent", "anio", "ciclo"])["severa"].mean()
           .ge(config.UMBRAL_MUNICIPIOS_SEQUIA).reset_index()
           .assign(nivel="estado").rename(columns={"cve_ent": "clave"}))
    nac = (t.groupby(["anio", "ciclo"])["severa"].mean()
           .ge(config.UMBRAL_MUNICIPIOS_SEQUIA).reset_index().assign(nivel="nacional", clave="00"))
    cols = GEO + ["anio", "ciclo", "severa"]
    return pd.concat([d[cols] for d in (mun, est, nac)], ignore_index=True)


def contexto_sequia(seq: pd.DataFrame, fin_ventana: int) -> pd.DataFrame:
    """Frecuencia histórica de sequía y estado actual por nivel/clave."""
    desde = pd.Timestamp(fin_ventana - config.VENTANA_ANIOS + 1, 1, 1)
    hist = seq[seq["fecha"] >= desde].copy()
    hist["cve_ent"] = hist["cvegeo"].str[:2]
    hist["d1"] = hist["categoria"] >= 1
    hist["d2"] = hist["categoria"] >= 2

    ultima = seq["fecha"].max()
    hoy = seq[seq["fecha"] == ultima].copy()
    hoy["cve_ent"] = hoy["cvegeo"].str[:2]
    hoy["en_sequia"] = hoy["categoria"] >= 1

    def bloque(hist_g, hoy_g, nivel):
        h = hist_g[["d1", "d2"]].mean().rename(columns={"d1": "frec_d1", "d2": "frec_d2"})
        a = pd.DataFrame({"cat_actual_max": hoy_g["categoria"].max(),
                          "pct_mun_en_sequia": hoy_g["en_sequia"].mean()})
        out = h.join(a)
        out.index.name = "clave"
        return out.reset_index().assign(nivel=nivel)

    mun = bloque(hist.groupby("cvegeo"), hoy.groupby("cvegeo"), "municipio")
    est = bloque(hist.groupby("cve_ent"), hoy.groupby("cve_ent"), "estado")
    nac = bloque(hist.assign(k="00").groupby("k"), hoy.assign(k="00").groupby("k"), "nacional")
    out = pd.concat([mun, est, nac], ignore_index=True)
    out["fecha_actual"] = ultima.date().isoformat()
    return out


# ---------------------------------------------------------------- Estadísticas

def preparar_anual(niveles: pd.DataFrame, flags: pd.DataFrame, deflactor: dict) -> pd.DataFrame:
    y = niveles.merge(flags, on=GEO + ["anio", "ciclo"], how="left")
    y["valor_real"] = y["valor"] * y["anio"].map(deflactor)
    y["sem_riego"] = np.where(y["modalidad"] == "riego", y["sembrada"], 0.0)
    seq = y["severa"].eq(True)
    norm = y["severa"].eq(False)  # sin dato del Monitor no cuenta en ninguno de los dos
    y["sem_seq"] = np.where(seq, y["sembrada"], 0.0)
    y["sin_seq"] = np.where(seq, y["siniestrada"], 0.0)
    y["sem_norm"] = np.where(norm, y["sembrada"], 0.0)
    y["sin_norm"] = np.where(norm, y["siniestrada"], 0.0)
    y["temp_seq"] = seq.astype(int)
    y["temp_norm"] = norm.astype(int)
    return y.drop(columns="severa")


def _div(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.divide(a, b, out=np.full_like(a, np.nan), where=b > 0)


def estadisticas(y: pd.DataFrame, llaves: list[str]) -> pd.DataFrame:
    """Estadísticos de la ventana. `y` tiene una fila por llaves + año."""
    y = y.copy()
    y["rend"] = np.where(y["volumen"] > 0, _div(y["volumen"], y["cosechada"]), np.nan)
    y["pmr_real"] = _div(y["valor_real"], y["volumen"])
    y["pmr_nom"] = _div(y["valor"], y["volumen"])
    y["ingreso_ha"] = _div(y["valor_real"], y["sembrada"])
    y["presente"] = (y["sembrada"] > 0).astype(int)
    y["ult"] = y["anio"] == y.groupby(llaves)["anio"].transform("max")

    g = y.groupby(llaves)
    q = g["rend"].quantile([0.25, 0.5, 0.75]).unstack()
    s = g[SUMAS + ["presente"]].sum()
    n_rend = g["rend"].count()

    out = pd.DataFrame({
        "n_anios": s["presente"],
        "anio_ultimo": g["anio"].max(),
        "sembrada_prom_ha": s["sembrada"] / s["presente"].clip(lower=1),
        "rend_p25": q[0.25], "rend_p50": q[0.5], "rend_p75": q[0.75],
        "cv_rendimiento": (g["rend"].std() / g["rend"].mean()).where(n_rend >= config.MIN_ANIOS_ESTADISTICA),
        "pmr_real_p50": g["pmr_real"].median(),
        "ingreso_ha_real_p50": g["ingreso_ha"].median(),
        "tasa_siniestro": _div(s["siniestrada"], s["sembrada"]),
        "tasa_siniestro_sequia": _div(s["sin_seq"], s["sem_seq"]),
        "tasa_siniestro_normal": _div(s["sin_norm"], s["sem_norm"]),
        "n_temporadas_sequia": s["temp_seq"],
        "n_temporadas_normales": s["temp_norm"],
        "pct_riego": _div(s["sem_riego"], s["sembrada"]),
    })
    # Para rendimiento con pocos años, los percentiles no dicen nada: solo mediana.
    poco = n_rend < config.MIN_ANIOS_ESTADISTICA
    out.loc[poco, ["rend_p25", "rend_p75"]] = np.nan

    ult = y[y["ult"]].set_index(llaves)
    out["pmr_nominal_ultimo"] = ult["pmr_nom"]
    out["pmr_real_ultimo"] = ult["pmr_real"]
    out["pmr_real_p50_previo"] = y[~y["ult"]].groupby(llaves)["pmr_real"].median()
    return out


def calcular(niveles, flags, deflactor):
    """Devuelve (por_combinacion, por_cultivo).

    por_combinacion: llave (nivel, clave, cultivo, ciclo, modalidad), como pide el .md.
    por_cultivo: resumen del cultivo en la ubicación sumando ciclos y modalidades.
    """
    y = preparar_anual(niveles, flags, deflactor)
    combo_keys = GEO + ["cultivo_id", "ciclo", "modalidad"]
    por_combo = estadisticas(y, combo_keys)

    cult_keys = GEO + ["cultivo_id"]
    anual_cult = y.groupby(cult_keys + ["anio"], as_index=False)[SUMAS].sum()
    # Una temporada con sequía cuenta una vez por año aunque el cultivo esté en dos ciclos.
    anual_cult["temp_seq"] = (anual_cult["temp_seq"] > 0).astype(int)
    anual_cult["temp_norm"] = ((anual_cult["temp_norm"] > 0) & (anual_cult["temp_seq"] == 0)).astype(int)
    por_cult = estadisticas(anual_cult, cult_keys)

    # Variabilidad del rendimiento solo en temporal: es la que refleja el riesgo de lluvia.
    temp = y[y["modalidad"] == "temporal"].groupby(cult_keys + ["anio"], as_index=False)[SUMAS].sum()
    por_cult["cv_rendimiento_temporal"] = estadisticas(temp, cult_keys)["cv_rendimiento"]

    # Reparto por ciclo (para "siembra ideal" según lo que se practica en la zona).
    reparto = (y.groupby(cult_keys + ["ciclo"])["sembrada"].sum().unstack(fill_value=0))
    reparto = reparto.div(reparto.sum(axis=1).replace(0, np.nan), axis=0)
    for c in ["OI", "PV", "PER"]:
        por_cult[f"pct_{c}"] = reparto[c] if c in reparto else 0.0

    # Rango de ingreso por ha dentro de la ubicación (percentil entre cultivos).
    elegibles = por_cult["n_anios"] >= config.MIN_ANIOS_ESTADISTICA
    por_cult["pctl_ingreso"] = (por_cult["ingreso_ha_real_p50"].where(elegibles)
                                .groupby(level=GEO).rank(pct=True))
    return por_combo.reset_index(), por_cult.reset_index()


# ---------------------------------------------------------------- Clasificaciones

def _valido(v):
    return v is not None and not (isinstance(v, float) and np.isnan(v))


def riesgo_hidrico(pct_riego, cv_temporal, frec_d2):
    """Puntaje 0-1 (heurística documentada en docs/cultivos-pipeline.md).

    score = 0.25 * amenaza + 0.75 * exposicion * (0.5 + 0.5 * vulnerabilidad)
      amenaza       = frecuencia de sequía D2+ en la zona (saturada en 30% de las lecturas)
      exposicion    = proporción de la superficie en temporal
      vulnerabilidad = CV del rendimiento en temporal (saturado en 0.4); 0.5 si no hay dato
    Un cultivo de riego conserva la parte de amenaza: la sequía también vacía presas
    y acuíferos, aunque eso aún no se mide (falta disponibilidad de acuíferos).
    """
    if not _valido(pct_riego):
        return None, None
    amenaza = min(frec_d2 / 0.3, 1.0) if _valido(frec_d2) else 0.5
    vuln = min(cv_temporal / 0.4, 1.0) if _valido(cv_temporal) else 0.5
    score = 0.25 * amenaza + 0.75 * (1 - pct_riego) * (0.5 + 0.5 * vuln)
    nivel = "bajo" if score < 0.33 else "medio" if score < 0.6 else "alto"
    return round(score, 2), nivel


def sensibilidad_sequia(tasa_seq, tasa_norm, n_seq, n_norm):
    """Compara la tasa de siniestro en temporadas con sequía severa contra las normales."""
    if n_seq < 1 or n_norm < 2 or np.isnan(tasa_seq) or np.isnan(tasa_norm):
        return "sin_evidencia"
    dif = tasa_seq - tasa_norm
    if dif >= 0.10 or tasa_seq >= 0.25:
        return "alta"
    if dif >= 0.03:
        return "media"
    return "baja"
