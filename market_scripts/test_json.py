
import json
import pandas as pd
import math

print("Cargando datasets...")

df_hist = pd.read_parquet(
    "market_data/dataset_agricola_por_estado.parquet"
)

df_pred = pd.read_parquet(
    "market_data/predicciones_agricolas_nacionales.parquet"
)

# --------------------------------------------------
# PREPARAR HISTÓRICO
# --------------------------------------------------

df_hist["fecha"] = pd.to_datetime(
    df_hist["fecha"], errors="coerce"
)

df_hist["precio_por_kilo"] = pd.to_numeric(
    df_hist["precio_por_kilo"], errors="coerce"
)

df_hist = df_hist.dropna(
    subset=["fecha", "precio_por_kilo", "estado", "producto"]
)

# Consolidar a promedio diario
df_hist = (
    df_hist.groupby(
        ["estado", "producto", "fecha"],
        as_index=False
    )
    .agg(
        precio_por_kilo=("precio_por_kilo", "mean")
    )
    .sort_values("fecha")
)

# --------------------------------------------------
# PREPARAR PREDICCIONES
# --------------------------------------------------

columna_fecha_pred = (
    "fecha_prediccion"
    if "fecha_prediccion" in df_pred.columns
    else "fecha"
)

posibles_columnas_precio = [
    "precio_estimado",
    "yhat",
    "precio_por_kilo",
    "precio",
    "valor"
]

columna_precio_pred = next(
    (
        col for col in posibles_columnas_precio
        if col in df_pred.columns
    ),
    None
)

if columna_precio_pred is None:
    raise ValueError(
        f"No se encontró columna de precio. "
        f"Columnas disponibles: {df_pred.columns.tolist()}"
    )

df_pred[columna_fecha_pred] = pd.to_datetime(
    df_pred[columna_fecha_pred], errors="coerce"
)

df_pred[columna_precio_pred] = pd.to_numeric(
    df_pred[columna_precio_pred], errors="coerce"
)

df_pred = df_pred.dropna(
    subset=[
        columna_fecha_pred,
        columna_precio_pred,
        "estado",
        "producto"
    ]
)

# Evitar duplicados de predicción por fecha
df_pred = (
    df_pred.groupby(
        ["estado", "producto", columna_fecha_pred],
        as_index=False
    )
    .agg(
        precio_estimado=(columna_precio_pred, "mean")
    )
)

# --------------------------------------------------
# CONSTRUIR JSON
# --------------------------------------------------

estructura_web = {}

# Incluir estados presentes en cualquiera de los dos archivos
estados = sorted(
    set(df_hist["estado"].unique()) |
    set(df_pred["estado"].unique())
)

for estado in estados:

    estructura_web[estado] = {}

    productos_hist = set(
        df_hist.loc[
            df_hist["estado"] == estado,
            "producto"
        ].unique()
    )

    productos_pred = set(
        df_pred.loc[
            df_pred["estado"] == estado,
            "producto"
        ].unique()
    )

    productos = sorted(productos_hist | productos_pred)

    for prod in productos:

        # Histórico del producto
        h = df_hist[
            (df_hist["estado"] == estado) &
            (df_hist["producto"] == prod)
        ].sort_values("fecha").tail(60)

        # Predicciones del producto
        p = df_pred[
            (df_pred["estado"] == estado) &
            (df_pred["producto"] == prod)
        ].sort_values(columna_fecha_pred)

        serie_combinada = {}

        # ------------------------------------------
        # DATOS REALES
        # ------------------------------------------

        for _, row in h.iterrows():

            fecha = row["fecha"].strftime("%Y-%m-%d")

            serie_combinada[fecha] = {
                "fecha": fecha,
                "real": round(float(row["precio_por_kilo"]), 2),
                "proyeccion": None
            }

        # ------------------------------------------
        # PREDICCIONES
        # ------------------------------------------

        for _, row in p.iterrows():

            fecha = row[columna_fecha_pred].strftime("%Y-%m-%d")

            if fecha not in serie_combinada:

                serie_combinada[fecha] = {
                    "fecha": fecha,
                    "real": None,
                    "proyeccion": None
                }

            serie_combinada[fecha]["proyeccion"] = round(
                float(row["precio_estimado"]), 2
            )

        # ------------------------------------------
        # UNIR ÚLTIMO PUNTO REAL CON PROYECCIÓN
        # ------------------------------------------

        if not h.empty and not p.empty:

            ultima_fecha = h.iloc[-1]["fecha"].strftime("%Y-%m-%d")

            ultimo_valor = round(
                float(h.iloc[-1]["precio_por_kilo"]), 2
            )

            if ultima_fecha in serie_combinada:

                serie_combinada[ultima_fecha]["proyeccion"] = (
                    ultimo_valor
                )

        # ------------------------------------------
        # ORDENAR Y GUARDAR
        # ------------------------------------------

        lista_ordenada = sorted(
            serie_combinada.values(),
            key=lambda x: x["fecha"]
        )

        estructura_web[estado][prod] = lista_ordenada

# --------------------------------------------------
# EXPORTAR
# --------------------------------------------------

archivo_salida = "market_front/src/datos_dashboard.json"

with open(
    archivo_salida,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        estructura_web,
        f,
        ensure_ascii=False,
        allow_nan=False
    )

print("\n¡JSON generado correctamente!")

print("Estados:", len(estructura_web))

print(
    "Productos:",
    sum(len(productos) for productos in estructura_web.values())
)

print(
    "Registros:",
    sum(
        len(serie)
        for estado in estructura_web.values()
        for serie in estado.values()
    )
)

print("Archivo:", archivo_salida)
