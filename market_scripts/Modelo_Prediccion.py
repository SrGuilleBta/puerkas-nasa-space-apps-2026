import matplotlib.pyplot as plt
import pandas as pd
from prophet import Prophet

print("Cargando el dataset estatal optimizado...")
df = pd.read_parquet("dataset_agricola_por_estado.parquet")

# 1. Inspeccionar qué productos tenemos disponibles si quieres elegir otro
print("\nEjemplos de productos en tu base:")
print(df["producto"].unique()[:10])

# 2. Elegir un producto y un estado para el modelo (Ejemplo: JITOMATE en NUEVO LEON)
producto_objetivo = (
    "JITOMATE"  # Cambia esto por el producto exacto que te interese
)
estado_objetivo = "NUEVO LEÓN"  # O el estado que prefieras

# Filtrar
df_filtrado = df[
    (df["producto"].str.contains(producto_objetivo, na=False))
    & (df["estado"].str.contains(estado_objetivo, na=False))
].copy()

# Prophet exige que las columnas se llamen exactamente 'ds' (fecha) y 'y' (precio a predecir)
df_prophet = df_filtrado[["fecha", "precio_por_kilo"]].rename(
    columns={"fecha": "ds", "precio_por_kilo": "y"}
)

# Ordenar por fecha
df_prophet = df_prophet.sort_values("ds").dropna()

print(
    f"\nDatos históricos encontrados para {producto_objetivo} en"
    f" {estado_objetivo}: {len(df_prophet)} registros"
)

if len(df_prophet) > 30:
  print("Entrenando modelo Prophet...")
  # Inicializar y entrenar el modelo
  modelo = Prophet(
      weekly_seasonality=True, yearly_seasonality=True, daily_seasonality=False
  )
  modelo.fit(df_prophet)

  # Crear un marco de tiempo para predecir los próximos 90 días (3 meses)
  futuro = modelo.make_future_dataframe(periods=90)
  prediccion = modelo.predict(futuro)

  print("¡Predicción generada con éxito!")

  # Mostrar un resumen de las próximas predicciones
  print(
      prediccion[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(5)
  )  # yhat es el precio estimado

  # Graficar resultados
  fig1 = modelo.plot(prediccion)
  plt.title(f"Predicción de Precio por Kilo: {producto_objetivo} ({estado_objetivo})")
  plt.xlabel("Fecha")
  plt.ylabel("Precio ($/kg)")
  plt.show()
else:
  print(
      "No hay suficientes datos históricos continuos para este producto/estado"
      " específico. Prueba con otro."
  )