import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

print("1. Cargando el dataset estatal limpio...")
df = pd.read_parquet("market_data/dataset_agricola_por_estado.parquet")

df["fecha"] = pd.to_datetime(df["fecha"])
df["precio_por_kilo"] = pd.to_numeric(df["precio_por_kilo"], errors="coerce")
df = df.dropna(subset=["fecha", "precio_por_kilo"])
df = df.sort_values(["estado", "producto", "fecha"])

grupos = list(df.groupby(["producto", "estado"]))
total_grupos = len(grupos)

fecha_sistema = pd.Timestamp.now().normalize()
fin_proyeccion = max(
    fecha_sistema + pd.Timedelta(days=30),
    pd.Timestamp(year=fecha_sistema.year + 1, month=1, day=1),
)

print(
    f"Fecha máxima en dataset global: {df['fecha'].max().strftime('%Y-%m-%d')}"
)
print(
    "Proyectando cada serie desde su último dato real hasta:"
    f" {fin_proyeccion.strftime('%Y-%m-%d')}\n"
)

resultados_predicciones = []
exitosos = 0

for i, ((producto, estado), grupo) in enumerate(grupos, 1):
  if len(grupo) >= 15:
    try:
      serie = grupo.sort_values("fecha").copy()
      serie["anio"] = serie["fecha"].dt.year
      serie["dia_anio"] = serie["fecha"].dt.dayofyear

      ultimo_precio = float(serie.iloc[-1]["precio_por_kilo"])
      ultima_fecha = serie.iloc[-1]["fecha"]
      anio_max = serie["anio"].max()

      # 1. NORMALIZACIÓN ANUAL Y PONDERACIÓN POR AÑOS RECIENTES
      # Calculamos la media de cada año para obtener el "Índice Estacional" (ej. 1.25 = 25% arriba de la media del año)
      medias_anuales = serie.groupby("anio")["precio_por_kilo"].transform(
          "mean"
      )
      serie["indice_estacional"] = serie["precio_por_kilo"] / medias_anuales

      # Damos más peso a los años recientes (decaimiento exponencial: 0.70 ^ años_atrás)
      serie["peso_anio"] = 0.70 ** (anio_max - serie["anio"])

      # Calcular curva de índice estacional ponderado por día del año
      def media_ponderada(g):
        return np.average(g["indice_estacional"], weights=g["peso_anio"])

      indices_por_dia = (
          serie.groupby("dia_anio").apply(media_ponderada).to_dict()
      )

      # Volatilidad relativa histórica para calibrar la textura de la línea
      retornos = serie["precio_por_kilo"].pct_change().dropna()
      volatilidad_diaria = (
          float(retornos.std()) if len(retornos) > 5 else 0.02
      )
      volatilidad_diaria = max(min(volatilidad_diaria, 0.045), 0.008)

      # 2. NIVEL BASE ACTUAL E INERCIA RECIENTE
      # Nivel base estimado del año actual
      datos_recientes = serie.tail(min(30, len(serie)))
      nivel_base_actual = float(datos_recientes["precio_por_kilo"].mean())

      # Índice estacional en la fecha de corte
      dia_corte = ultima_fecha.dayofyear
      vecinos_corte = [
          indices_por_dia[d]
          for d in range(dia_corte - 5, dia_corte + 6)
          if d in indices_por_dia
      ]
      indice_en_corte = (
          float(np.mean(vecinos_corte)) if vecinos_corte else 1.0
      )

      # Ancla de nivel desestacionalizado
      nivel_ancla = (
          ultimo_precio / indice_en_corte
          if indice_en_corte > 0
          else ultimo_precio
      )

      inicio_proy = ultima_fecha + pd.Timedelta(days=1)
      fechas_futuras = pd.date_range(
          start=inicio_proy, end=fin_proyeccion, freq="D"
      )

      valores_proyectados = []
      np.random.seed(abs(hash(f"{producto}_{estado}")) % (2**32))

      # Estado del ruido autocorrelacionado (Ornstein-Uhlenbeck)
      ruido_acumulado = 0.0

      for step, fecha_fut in enumerate(fechas_futuras):
        d_anio = fecha_fut.dayofyear

        # Suavizado estacional en ventana de ±7 días para evitar escalones bruscos
        pesos_ventana = []
        vals_ventana = []
        for tol in range(-7, 8):
          d_ajustado = ((d_anio + tol - 1) % 365) + 1
          if d_ajustado in indices_por_dia:
            # Peso gaussiano: los días más cercanos al día objetivo pesan más
            pesos_ventana.append(np.exp(-(tol**2) / 18.0))
            vals_ventana.append(indices_por_dia[d_ajustado])

        indice_dia = (
            float(np.average(vals_ventana, weights=pesos_ventana))
            if vals_ventana
            else 1.0
        )

        # Reversión gradual del nivel: empieza en el nivel exacto de corte y converge suavemente al nivel base
        factor_decaimiento = np.exp(-step / 45.0)
        nivel_dinamico = (nivel_ancla * factor_decaimiento) + (
            nivel_base_actual * (1.0 - factor_decaimiento)
        )

        precio_tendencia = nivel_dinamico * indice_dia

        # Transición suave en los primeros 10 días para empatar sin quiebres con el último punto real
        peso_empalme = np.exp(-step / 5.0)
        precio_base = (ultimo_precio * peso_empalme) + (
            precio_tendencia * (1.0 - peso_empalme)
        )

        # 3. RUIDO ORGÁNICO AUTOCORRELACIONADO (Ondas cortas de mercado con reversión a la curva)
        choque_aleatorio = np.random.normal(
            0, volatilidad_diaria * precio_base * 0.45
        )
        ruido_acumulado = (0.72 * ruido_acumulado) + choque_aleatorio

        # En el día 0 el ruido es pequeño para conectar limpio con el último dato real
        factor_ruido = min(1.0, (step + 1) / 4.0)
        precio_final = max(precio_base + (ruido_acumulado * factor_ruido), 1.0)

        valores_proyectados.append(round(precio_final, 2))

      pred_futura = pd.DataFrame({
          "fecha_prediccion": fechas_futuras,
          "precio_estimado": valores_proyectados,
          "producto": producto,
          "estado": estado, 
      })

      resultados_predicciones.append(pred_futura)
      exitosos += 1
    except Exception:
      continue

if resultados_predicciones:
  df_final_preds = pd.concat(resultados_predicciones, ignore_index=True)
  archivo_salida = "market_data/predicciones_agricolas_nacionales.parquet"
  df_final_preds.to_parquet(archivo_salida, index=False)
  print(
      f"¡Modelado finalizado! {exitosos} series proyectadas guardadas en"
      f" '{archivo_salida}'."
  )