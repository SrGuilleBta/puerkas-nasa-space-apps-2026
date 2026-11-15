"""Carga y limpieza de cada fuente. Cada función devuelve un DataFrame ya normalizado."""

import json
import re
import unicodedata

import pandas as pd

from . import config

# Mismo orden en todos los años. 2015-2020 cambian el nombre de las columnas 17 y 23
# ("Nomcultivo Sin Um" y "Precio"), así que se asignan por posición.
COLUMNAS_SIAP = [
    "anio", "cve_ent", "estado", "id_ddr", "ddr", "id_cader", "cader",
    "cve_mun", "municipio", "id_ciclo", "ciclo", "id_modalidad", "modalidad",
    "id_unidad", "unidad", "id_cultivo", "cultivo", "sembrada", "cosechada",
    "siniestrada", "volumen", "rendimiento", "pmr", "valor",
]
NUMERICAS = ["sembrada", "cosechada", "siniestrada", "volumen", "valor"]


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def cargar_siap() -> pd.DataFrame:
    """Une los CSV anuales y deja una fila por año-municipio-cultivo-ciclo-modalidad.

    SIAP puede partir un municipio en varios CADER (p. ej. Ensenada / San Quintín),
    así que se suman superficies, volumen y valor. Rendimiento y precio se recalculan
    después como cocientes ponderados; los del CSV no se usan.
    """
    archivos = sorted(config.SIAP_DIR.glob("cierre_agricola_mun_*.csv"))
    if not archivos:
        raise FileNotFoundError(f"No hay CSV de SIAP en {config.SIAP_DIR}")

    marcos = []
    for ruta in archivos:
        d = pd.read_csv(ruta, encoding="latin1", dtype=str)
        if len(d.columns) != len(COLUMNAS_SIAP):
            raise ValueError(f"{ruta.name}: se esperaban 24 columnas, hay {len(d.columns)}")
        d.columns = COLUMNAS_SIAP
        marcos.append(d)
    df = pd.concat(marcos, ignore_index=True)

    for c in NUMERICAS:
        # 2021 y 2022 traen algunos valores con separador de miles ("10,271").
        df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce").fillna(0)
    df["anio"] = df["anio"].astype(int)
    df["cve_ent"] = df["cve_ent"].str.zfill(2)
    # Idmunicipio de SIAP es la clave municipal de INEGI: CVEGEO = estado + municipio.
    df["cvegeo"] = df["cve_ent"] + df["cve_mun"].str.zfill(3)
    df["ciclo"] = df["ciclo"].map(config.CICLOS)
    df["modalidad"] = df["modalidad"].map(config.MODALIDADES)
    for c in ["cultivo", "unidad", "estado", "municipio"]:
        df[c] = df[c].str.strip()

    # Id estable del cultivo. Si un nombre aparece en varias unidades (flores en
    # gruesa y en planta), la unidad entra en el id para no mezclar volúmenes.
    unidades = df.groupby("cultivo")["unidad"].nunique()
    multi = df["cultivo"].map(unidades) > 1
    df["cultivo_id"] = df["cultivo"].map(slug)
    df.loc[multi, "cultivo_id"] = (df.loc[multi, "cultivo"] + " " + df.loc[multi, "unidad"]).map(slug)

    llave = ["anio", "cve_ent", "cvegeo", "cultivo_id", "ciclo", "modalidad"]
    agregado = df.groupby(llave, as_index=False)[NUMERICAS].sum()
    return agregado, df


def nombres(df_crudo: pd.DataFrame):
    """Nombres más recientes de estados, municipios y cultivos."""
    reciente = df_crudo.sort_values("anio")
    estados = reciente.groupby("cve_ent")["estado"].last().to_dict()
    municipios = reciente.groupby("cvegeo")["municipio"].last().to_dict()
    cultivos = reciente.groupby("cultivo_id").agg(nombre=("cultivo", "last"), unidad=("unidad", "last"))
    return estados, municipios, cultivos


def cargar_sequia() -> tuple[pd.DataFrame, dict]:
    """Monitor de Sequía en formato largo: cvegeo, fecha, categoria (-1 sin sequía, 0=D0 ... 4=D4)."""
    if not config.SEQUIA_XLSX.exists():
        raise FileNotFoundError(f"Falta {config.SEQUIA_XLSX}. Corre: python -m pipeline.cultivos descargar")
    x = pd.read_excel(config.SEQUIA_XLSX, sheet_name="MUNICIPIOS", dtype={"CVE_CONCATENADA": str})
    x["cvegeo"] = x["CVE_CONCATENADA"].str.zfill(5)
    nombres_mun = x.set_index("cvegeo")[["NOMBRE_MUN", "ENTIDAD"]].to_dict("index")
    fechas = [c for c in x.columns if not isinstance(c, str)]
    largo = x.melt(id_vars="cvegeo", value_vars=fechas, var_name="fecha", value_name="cat")
    largo["fecha"] = pd.to_datetime(largo["fecha"])
    largo["categoria"] = (
        largo["cat"].astype(str).str.extract(r"D(\d)")[0].astype(float).fillna(-1).astype(int)
    )
    return largo[["cvegeo", "fecha", "categoria"]], nombres_mun


def cargar_ecocrop() -> pd.DataFrame:
    if not config.ECOCROP_CSV.exists():
        raise FileNotFoundError(f"Falta {config.ECOCROP_CSV}. Corre: python -m pipeline.cultivos descargar")
    e = pd.read_csv(config.ECOCROP_CSV, encoding="latin1")
    return e.drop_duplicates("ScientificName").set_index("ScientificName")


def cargar_deflactor() -> dict[int, float]:
    """Factor para pasar pesos de cada año a pesos de ANIO_BASE_PRECIOS.

    Se arma un índice encadenando la inflación promedio anual (equivale al INPC
    promedio anual con base distinta, que se cancela al dividir).
    """
    if not config.INFLACION_CSV.exists():
        raise FileNotFoundError(f"Falta {config.INFLACION_CSV}. Corre: python -m pipeline.cultivos descargar")
    inf = pd.read_csv(config.INFLACION_CSV).set_index("anio")["inflacion_promedio_pct"]
    indice, nivel = {}, 100.0
    for anio in sorted(inf.index):
        nivel *= 1 + inf[anio] / 100
        indice[int(anio)] = nivel
    base = indice[config.ANIO_BASE_PRECIOS]
    return {a: base / v for a, v in indice.items()}


def cargar_curado() -> dict:
    with open(config.CURADO_JSON, encoding="utf-8") as f:
        return json.load(f)["cultivos"]
