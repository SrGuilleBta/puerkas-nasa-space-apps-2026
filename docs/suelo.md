# Módulo Suelo (borrador)

Qué va a tener el módulo Suelo y qué necesita el backend. Es la base para empezar a programar;
se ajusta conforme avancemos. Las fuentes generales están en [datos.md](datos.md).

## Para qué sirve

Decirle al agricultor **cómo está su suelo hoy y hacia dónde va**: si tiene agua, si la está
perdiendo, si está en riesgo de erosión y cuánta materia orgánica tiene. Esos datos los usa el
Planificador para recomendar rotaciones.

Lo que pide el reto y cubre este módulo: *soil moisture, evaporation, long‑term water trends,
erosion reduction, organic matter improvement* (y opcional *frost risk*, *vegetation stress*).

## Secciones de la pantalla

| # | Sección | Qué muestra | Fuente | Prioridad |
|---|---|---|---|---|
| 1 | **Estado general** | Semáforo 🟢🟡🔴: humedad actual vs. promedio histórico de ese mes | NASA POWER (cálculo propio) | MVP |
| 2 | **Humedad del suelo** | Superficie, zona de raíz y perfil completo | NASA POWER (`GWETTOP`, `GWETROOT`, `GWETPROF`); Open-Meteo para hoy/pronóstico; SMAP después | MVP |
| 3 | **Temperatura del suelo** | Temperatura de la superficie del suelo | NASA POWER (`TS`), Open-Meteo (`soil_temperature_0cm`) | MVP |
| 4 | **Pérdida de agua (evaporación)** | Cuánta agua se va del suelo | NASA POWER / Open-Meteo (ET0); ECOSTRESS después | MVP |
| 5 | **Propiedades del suelo** | pH, textura (arcilla/arena/limo), materia orgánica (carbono) | SoilGrids | MVP |
| 6 | **Riesgo de erosión** | Pendiente del terreno + lluvias fuertes | SRTM + GPM/IMERG (o lluvia de POWER) | MVP |
| 7 | **Agua subterránea** | Tendencia de largo plazo: ¿la región se está secando? | GRACE / GRACE-FO | Recomendado |
| 8 | **Tendencia de humedad** | Gráfica mensual de ~20 años | NASA POWER | MVP |
| 9 | Cobertura del suelo | ¿El terreno está sin plantas? (NDVI) | MODIS / Landsat | Fase 2 |
| 10 | Suelo congelado | Riesgo de helada en el suelo | SMAP freeze/thaw o `TS` de POWER | Opcional |

## Endpoints propuestos

Todos reciben **`municipio`** (el del selector de arriba, ej. `Monterrey, NL`) o, si no, `lat` y `lon`.
Con municipio se usa su **punto de campo agrícola** (`lat_suelo`/`lon_suelo` en
`backend/app/services/municipios.py`, de Guille), porque en la ciudad SoilGrids no tiene datos.
La pantalla de Suelo usa el municipio que eligió el agricultor.

| Ruta | Parámetros extra | Devuelve | Sección |
|---|---|---|---|
| `GET /api/suelo/actual` | — | Humedad (superficie, ~20 cm) y temperatura del suelo de hoy | 2, 3 |
| `GET /api/suelo/dia` | `fecha` | Lo mismo para un día (pasado: POWER, futuro: Open-Meteo) | 2, 3 |
| `GET /api/suelo/estado` | — | Semáforo y % vs. promedio histórico del mes | 1 |
| `GET /api/suelo/historico` | `inicio`, `fin` | Serie mensual de humedad, temperatura y evaporación | 4, 8 |
| `GET /api/suelo/propiedades` | — | pH, arcilla, arena, limo, carbono orgánico y textura | 5 |
| `GET /api/suelo/erosion` | — | Pendiente (SRTM), lluvias fuertes (POWER) y nivel de riesgo | 6 |
| `GET /api/suelo/agua-subterranea` | — | Tendencia de GRACE en la región | 7 |

## Variables por fuente

| Fuente | Variables | Notas |
|---|---|---|
| NASA POWER | `GWETTOP`, `GWETROOT`, `GWETPROF`, `TS`, `PRECTOTCORR` | Sin llave. Humedad viene de 0 a 1. `-999` = sin dato. ~50 km de resolución |
| Open-Meteo | `soil_moisture_0_to_1cm`, `soil_moisture_9_to_27cm`, `soil_temperature_0cm`, `et0_fao_evapotranspiration` | Sin llave. Solo se probó la temperatura a 0 cm; verificar las demás |
| SoilGrids | `phh2o`, `clay`, `sand`, `silt`, `soc` (capas 0–5 y 5–15 cm) | Sin llave. Valores escalados (pH ×10, arcilla en g/kg). Da `null` en zonas urbanas |
| SRTM | Elevación → pendiente | Fuente de descarga por definir |
| GPM / IMERG | Lluvia diaria, eventos extremos | Pide login de Earthdata |
| GRACE / GRACE-FO | Anomalía de almacenamiento de agua | Pide login de Earthdata. Resolución muy gruesa (cientos de km): solo tendencia regional |
| SMAP | Humedad superficial, freeze/thaw | Pide login de Earthdata |

## Cálculos del backend

- **Humedad vs. otros años** (antes "estado de sequía"): con **SMAP**, no con NASA POWER. POWER cambió de modelo el 1-oct-2026
  (MERRA-2 → GEOS-IT; en Yucatán la humedad bajó 10 puntos de golpe ese día) y comparar el dato nuevo
  contra el historial viejo daba sequías falsas (Yucatán salía D4 y el Monitor de Sequía de CONAGUA
  del 31-oct decía "sin sequía"). SMAP mide con el mismo instrumento desde 2015: se compara el promedio
  de los últimos 30 días contra el mismo periodo de cada año (11 años) con las categorías D0–D4.
  Validado contra CONAGUA (31-oct-2026): Nuevo León y Yucatán "sin sequía" en los dos.
  Las mediciones se guardan en `backend/data/suelo/smap/` (no se sube a git) y se precargan con
  `python -m scripts.precargar_suelo`.
- **SMAP**: cada archivo diario pesa ~600 MB, así que se pide solo el píxel del punto con OPeNDAP de
  Earthdata (~1–2 s por día). El renglón/columna de la cuadrícula EASE-Grid 2.0 de 9 km se calcula con
  la proyección oficial (verificado: cae en 25.80, −100.04 para Monterrey).
- **Textura**: clasificar arcilla/arena/limo con el triángulo de texturas (USDA).
- **Erosión**: no se calcula un "riesgo" propio; se dan la pendiente con su clase FAO y los días
  de lluvia ≥20 mm (R20mm).
- **Conversiones**: `-999` → `null`, pH ÷ 10, humedad 0–1 → %.

## Estado actual (rama `suelo`)

Todos los endpoints de la tabla ya funcionan (probados en lat 25.9, lon -100.2):

| Endpoint | Ejemplo de respuesta |
|---|---|
| `/actual` | Humedad superficie 48 %, raíz 43 %, suelo 17.5 °C (11 nov 2026) |
| `/estado` | Sin sequía: 43 % vs. promedio de noviembre 40.4 % (percentil 70, 20 años) |
| `/historico` | Serie mensual con humedad, temperatura y evaporación (`EVLAND`, mm/día) |
| `/propiedades` | pH 7.9, franco arcilloso, carbono orgánico 20.4 g/kg, materia orgánica estimada 3.52 % (0–5 cm) |
| `/erosion` | Pendiente 2.7 % ("ligeramente inclinado", FAO) y días/año con lluvia ≥20 mm |
| `/agua-subterranea` | −0.7 cm/año: la región pierde agua almacenada (GRACE 2002–2026) |
| `/smap` | Humedad superficial **medida** por satélite: 19 % vol. (13 nov 2026, pasada PM), últimos 10 días |
| `/raiz` | Humedad de la zona de raíces (0–100 cm) con **SMAP L4** (modelo de NASA corregido con SMAP, no medición directa) |
| `/retencion` | Humedad SMAP + lluvia diaria (POWER) de 45 días: cuánto sube la humedad con cada lluvia y qué tan rápido baja |
| `/cobertura` | NDVI de **MODIS** (250 m): promedio por mes de 3 años, meses de suelo desnudo (NDVI ≤ 0.1, USGS) y el último valor |

Cómo correrlo: poner `EARTHDATA_TOKEN` en `.env` y `docker compose up -d --force-recreate backend`
(se agregó `h5py` para leer GRACE). La primera consulta a `/erosion` y `/agua-subterranea` tarda
porque descarga SRTM (~25 MB) y GRACE (~46 MB); después queda en `backend/data/` (no se sube a git).

Regla del equipo: **nada de deducciones propias**. Cada clasificación usa una regla oficial citable:

| Dato | Regla | Fuente |
|---|---|---|
| Humedad vs. otros años (`/estado`) | Percentil del promedio de humedad **SMAP** de los últimos 30 días vs. el mismo periodo de cada año desde 2015: D0 ≤30, D1 ≤20, D2 ≤10, D3 ≤5, D4 ≤2 | U.S. Drought Monitor / Monitor de Sequía de América del Norte |
| Calidad SMAP (`/smap`) | `retrieval_qual_flag` bit 0 = 0 → "calidad recomendada"; si no, se avisa en pantalla | Equipo de SMAP (NSIDC) |
| Clase de pendiente (`/erosion`) | 0–0.2 % plano … 2–5 % ligeramente inclinado … >60 % muy escarpado | FAO, *Guidelines for Soil Description* (2006) |
| Lluvia muy intensa (`/erosion`) | Días con lluvia ≥20 mm | Índice R20mm, ETCCDI (OMM) |
| Textura (`/propiedades`) | Triángulo de texturas | USDA |
| Factor LS (`/erosion`) | (As/22.13)^0.4 × (sen β/0.0896)^1.3, flujo D8 sobre SRTM; LS = 1 es la parcela estándar RUSLE | RUSLE (USDA), Moore y Burch (1986) |
| Cobertura (`/cobertura`) | NDVI ≤ 0.1 suelo desnudo; 0.2–0.3 matorral/pastizal; ≥ 0.6 vegetación densa | USGS |
| Materia orgánica estimada (`/propiedades`) | Carbono orgánico × 1.724 (factor empírico de Van Bemmelen; en algunos suelos el real se acerca a 2.0, Pribyl 2010) | NOM-021-SEMARNAT-2000 |
| Tendencia de GRACE | Regresión lineal de la serie; negativa = pierde agua | Cálculo directo sobre datos NASA |

La materia orgánica se marca como **estimada**: el dato directo es el carbono orgánico de SoilGrids.

## Tabla fija de SoilGrids

El suelo no cambia (SoilGrids es un mapa fijo), así que **no se consulta cada vez**. Un script consulta
una sola vez el punto de campo de cada municipio y lo guarda en
`backend/data/suelo/soilgrids_municipios.json` (este archivo **sí se sube** al repo, como los CSV de SIAP).

- La app lee de la tabla: responde en milisegundos, sin el límite de ~5 consultas/min de SoilGrids.
- Si el punto no está en la tabla, consulta SoilGrids **una vez y lo agrega a la tabla** (la tabla se
  llena sola). Los puntos sin datos (ciudad, agua) no se guardan.
- Al agregar municipios en `services/municipios.py`, correr (salta los que ya están):

  ```bash
  docker compose exec backend python -m scripts.generar_suelo_municipios
  ```
  Espera 13 s entre consultas para no pasar el límite (~2,470 municipios ≈ 9 horas; se guarda
  después de cada punto, así que se puede cortar y continuar).
- Trae las capas 0–5, 5–15 y 15–30 cm, así que también sirve para el pH de la Principal
  (pendiente de platicar con Guille).

## Selector: por estado

El selector de arriba tiene los **32 estados** y los datos son por estado (`services/municipios.py`).
El punto de campo de cada estado es **el píxel de cultivo más cercano a la capital** según el mapa de
cobertura de NASA MODIS (MCD12Q1 v061, 500 m, clases IGBP 12 "cultivo" y 14 "mosaico de cultivo"),
elegido con `python -m scripts.buscar_cultivo` (una consulta por estado, ~1 min en total). Casi todos
quedan a 1–10 km de la capital; Baja California Sur a ~47 km (alrededor de La Paz es desierto).
Excepción: en CDMX el cultivo más cercano caía en el Estado de México, así que se usa uno en Tláhuac.

Antes se usaba "el punto más cercano a la capital donde SoilGrids tiene dato", pero al verificar con
MODIS solo 7 de 32 caían en cultivo (Jalisco caía en ciudad y CDMX en Gustavo A. Madero).

Al cambiar los puntos hay que volver a bajar sus datos: la app lo hace sola la primera vez que se
abre cada estado, o de una vez con `python -m scripts.precargar_suelo`.

## Para el Planificador

Quien haga el Planificador **no necesita llamar a cada endpoint**: `GET /api/suelo/resumen?municipio=...`
(en el front: `getResumen({ municipio })` de `frontend/src/api/suelo.js`) devuelve todo lo de suelo
ya clasificado con reglas oficiales. Si una fuente no responde, su sección viene en `null` y el motivo
en `faltantes` (la primera vez puede tardar; con `scripts/precargar_suelo.py` queda guardado).

Ejemplo (Apodaca, Nuevo León):

```json
{
 "estado": "Nuevo León",
 "humedad_vs_normal": { "clase": "normal o más húmedo de lo normal", "codigo_referencia": null, "percentil": 81.8,
                        "humedad_pct_volumen": 21.9, "promedio_historico_pct_volumen": 19.5 },
 "agua_subterranea": { "tendencia_cm_por_anio": -0.7, "lectura": "La región está perdiendo agua almacenada" },
 "cobertura": { "clase_actual": "vegetación densa", "meses_suelo_desnudo": [], "mes_menor_cobertura": "feb",
                "ndvi_por_mes": { "ene": 0.488, "feb": 0.379, "...": "..." } },
 "terreno": { "pendiente_pct": 4.2, "clase_pendiente_fao": "ligeramente inclinado", "factor_ls_rusle": 0.64,
              "dias_lluvia_muy_intensa_por_anio": 4.4 },
 "propiedades": { "textura_usda": "franco arcilloso", "ph": 7.7, "carbono_organico_g_kg": 22.9,
                  "materia_organica_estimada_pct": 3.95 },
 "condiciones_hoy": { "evaporacion_mm_dia": 1.8, "temperatura_superficie_c": 18.79 },
 "faltantes": {}
}
```

### Qué parte del reto cubre cada dato y cómo lo puede usar el Planificador

El módulo Suelo **solo describe** el suelo; las **recomendaciones** de rotación son del Planificador
y deben salir de una regla citable (p. ej. guías de la FAO), no inventadas.

| Lo que pide el reto | Dato en `/resumen` | Pregunta que ayuda a contestar en la rotación |
|---|---|---|
| *Soil moisture*, *rainfall/drought patterns* | `humedad_vs_normal` (SMAP) | ¿La temporada viene más seca de lo normal? → considerar cultivos de menor consumo de agua |
| *Long-term water trends*, prioridad *water use* | `agua_subterranea` (GRACE) | ¿El riego es sostenible en la región? Si baja, priorizar cultivos de menor consumo |
| *Vegetation stress*, prioridad *erosion reduction* | `cobertura.meses_suelo_desnudo`, `ndvi_por_mes` (MODIS) | ¿En qué meses queda el terreno sin protección? → ahí cabe un cultivo de cobertura |
| *SRTM / elevation*, *extreme precipitation*, *erosion reduction* | `terreno` (pendiente FAO, factor LS RUSLE, días R20mm) | ¿Qué tanto se pierde suelo con la lluvia? Con LS > 1 o pendientes altas, preferir cultivos que cubran el suelo |
| *Local soil information* | `propiedades` (textura USDA, pH) | ¿Qué cultivos toleran ese pH y esa textura? (cruzar con los requisitos de EcoCrop del módulo Cultivos) |
| Prioridad *organic matter improvement* | `propiedades.carbono_organico_g_kg`, `materia_organica_estimada_pct` | Punto de partida: con poca materia orgánica, rotar con leguminosas o dejar rastrojo |
| Prioridad *nitrogen-fixing potential* | (no es de Suelo) | Viene de la familia del cultivo (leguminosas) en el módulo Cultivos |
| *Evaporation* | `condiciones_hoy.evaporacion_mm_dia` (POWER) | Cuánta agua pierde el suelo hoy |
| *Heat stress*, *frost risk* | (no es de Suelo) | Módulo Clima (temperaturas máximas y mínimas) |

### Límites que el Planificador debe conocer
- **Datos por estado**: un punto de cultivo por estado (MODIS), cerca de la capital; no representa todo el estado.
- `humedad_vs_normal` mide solo humedad del suelo: **no es sequía oficial** (en algunos estados del sur
  SMAP marca más seco que el Monitor de Sequía de CONAGUA).
- SMAP marca muchas mediciones como "calidad no recomendada" (vegetación densa, interferencia).
- GRACE es regional (~300 km) y mide agua total, no solo la subterránea.

## Archivos

| Capa | Archivo |
|---|---|
| Router | `backend/app/routers/suelo/endpoints.py` |
| Servicios | `backend/app/services/suelo/`: `nasa_power.py`, `soilgrids.py`, `srtm.py`, `grace.py`, `smap.py` (L3 y L4), `modis.py` |
| Scripts | `backend/scripts/`: `buscar_cultivo.py` (puntos de cultivo), `generar_suelo_municipios.py` (tabla SoilGrids), `precargar_suelo.py` (SMAP, SRTM, MODIS) |
| Front (API) | `frontend/src/api/suelo.js` |
| Front (pantalla) | `frontend/src/pages/Suelo/Suelo.jsx` |
| Menú | Agregar "Suelo" en `frontend/src/App.jsx` |

## Técnico

- Caché en memoria por (lat, lon, fechas): SoilGrids y POWER son lentos.
- Usar coordenadas de campo, no de centro de ciudad.
- Llaves de Earthdata (SMAP, IMERG, GRACE) en `.env`, nunca en el código.

## Por decidir con el equipo

1. Principal y Clima muestran humedad del suelo: ¿llaman a `/api/suelo` en vez de pedirla por su cuenta?
2. Formato del semáforo para que lo use el Planificador.
3. ~~¿De dónde bajamos SRTM?~~ Decidido: SRTMGL1 (30 m) de LP DAAC con el token de Earthdata.
   Se baja el mosaico de 1°×1° la primera vez (~25 MB) y se guarda en `backend/data/srtm/`.
4. ~~¿GRACE e IMERG entran al MVP?~~ Decidido: **GRACE sí entra** (hay que crear cuenta de
   Earthdata). **IMERG se deja para después**; mientras, la lluvia sale de NASA POWER.
