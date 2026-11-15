# Mercado

Precios **al consumidor** (Profeco, programa "Quién es Quién en los Precios") por kilo, de 58 productos en 32 estados,
con una proyección. Sale en la pantalla **Market**, en la tarjeta de "Cultivos activos" de Principal (precio y tendencia)
y en Noticias (cuando un precio cambia 5 % o más en 30 días).

Son precios de supermercado, no de productor: sirven para ver tendencias, no como precio de venta en "Costos e ingresos"
(ahí se usa SIAP).

## De dónde salen los datos

| Pieza | Qué hace |
|---|---|
| `market_scripts/actualizar_profeco.py` | Descarga los archivos de Profeco a `QQP/` (fuera de git; se cambia con `QQP_CARPETA`) |
| `market_data/dataset_agricola_por_estado.parquet` | Precios reales limpios (2015 al último dato) |
| `market_scripts/Entrenamiento_Masivo.py` | Proyección diaria por producto y estado (curva estacional, vuelve al nivel reciente y lleva variación simulada de corto plazo) → `market_data/predicciones_agricolas_nacionales.parquet` |
| `market_scripts/exportar_json.py` | Traduce productos al inglés y genera `backend/data/mercado` (32 archivos por estado + `meta.json`, ~5 MB, fuera de git) |
| `backend/app/services/mercado.py` | Lee esos archivos y arma estados, productos, series y tendencias |

Dependencias de los scripts: `market_scripts/requirements.txt`. `docker compose up` corre `exportar_json.py` si falta
`backend/data/mercado/meta.json` (sin traducción automática: usa el glosario y `market_data/cache_traducciones.json`).
Para regenerar a mano: `python market_scripts/exportar_json.py`.

Los precios reales de los últimos 90 días son diarios y los anteriores semanales (la gráfica de 1 año se ve igual);
la proyección es diaria 30 días y luego semanal.

## API

- `GET /api/mercado/estados?municipio=` estados, fecha del último dato real, `desactualizado` (más de 14 días) y el estado sugerido.
- `GET /api/mercado/productos?estado=` productos con último precio, cambio de 30 días y cambio proyectado a 30 días.
- `GET /api/mercado/serie?estado=&productos=A,B&rango=semana|mes|anio` hasta 10 productos; el rango se mide alrededor del último dato real.

Un cultivo del catálogo se liga con su producto por nombre en español y por las excepciones de `CULTIVO_DEL_PRODUCTO`
(jitomate, tomate verde, nopal...): 55 de los 58 productos tienen cultivo; no lo tienen alubia, kiwi y pimiento.

## Pendiente

- **Datos viejos**: el último dato real es del 31 de julio de 2026 y la proyección termina el 1 de enero de 2027. La pantalla
  avisa cuando pasan 14 días, y la noticia de precios no sale con datos viejos. Hay que correr `actualizar_profeco.py` y volver a
  generar el parquet con los scripts de `market_scripts` (no lo probé: descarga archivos grandes de datos.gob.mx).
- **La proyección lleva ruido simulado** (decisión del autor): se ve como un precio real, pero esa variación no tiene
  información. La pantalla lo dice en la nota al pie.
- Sin demanda real ni precios al productor diarios (SNIIM no tiene API).
- `Modelo_Prediccion.py` es un ejemplo con Prophet para un solo producto; no lo usa nada y su ruta de datos está desactualizada.
