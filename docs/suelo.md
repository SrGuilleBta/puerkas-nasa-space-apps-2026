# Módulo Suelo

Qué muestra el módulo Suelo, de dónde salen sus datos y cómo está armado el backend. Ya está
implementado y conectado a Principal, al popup del cultivo del Planificador y a las alertas. Las
fuentes generales están en [datos.md](datos.md).

## Para qué sirve

Decirle al agricultor **cómo está su suelo hoy y hacia dónde va**: si tiene agua, si la está
perdiendo, si está en riesgo de erosión y cuánta materia orgánica tiene. Esos datos los usa el
Planificador para recomendar rotaciones.

Lo que pide el reto y cubre este módulo: *soil moisture, evaporation, long‑term water trends,
erosion reduction, organic matter improvement* (y opcional *frost risk*, *vegetation stress*).

## Secciones de la pantalla

| # | Sección | Qué muestra | Fuente | Estado |
|---|---|---|---|---|
| 1 | **Estado general** | Humedad actual vs. otros años en esta época (percentil, categorías D0–D4) | NASA SMAP (ver "Cálculos") | Hecha |
| 2 | **Humedad del suelo** | Superficie, zona de raíz y perfil completo | NASA POWER (`GWETTOP`, `GWETROOT`, `GWETPROF`); SMAP (medida) y SMAP L4 (raíz) | Hecha |
| 3 | **Temperatura del suelo** | Temperatura de la superficie del suelo | NASA POWER (`TS`) | Hecha |
| 4 | **Pérdida de agua (evaporación)** | Cuánta agua se va del suelo | NASA POWER (`EVLAND`) | Hecha |
| 5 | **Propiedades del suelo** | pH, textura (arcilla/arena/limo), materia orgánica (carbono) | SoilGrids | Hecha |
| 6 | **Riesgo de erosión** | Pendiente del terreno + lluvias fuertes | SRTM + lluvia de NASA POWER (R20mm) | Hecha |
| 7 | **Agua subterránea** | Tendencia de largo plazo: ¿la región se está secando? | GRACE / GRACE-FO | Hecha |
| 8 | **Tendencia de humedad** | Gráfica mensual de ~20 años | NASA POWER | Hecha |
| 9 | Cobertura del suelo | ¿El terreno está sin plantas? (NDVI) | MODIS (MOD13, 250 m) | Hecha |
| 10 | Suelo congelado | Riesgo de helada en el suelo | SMAP freeze/thaw o `TS` de POWER | Opcional, no hecha |
| 11 | **Hacia dónde va el suelo** (estimación a 7 días) | Humedad de la zona de raíz, temperatura del suelo y pérdida de agua de los próximos días, con la lluvia pronosticada y un aviso si viene lluvia fuerte. **Es una estimación, no una medición**: se dibuja punteada | Último dato de NASA POWER + Open-Meteo (lluvia, ET0 de la FAO, temperatura del suelo) | Hecha |

## Endpoints

Todos reciben **`municipio`** (el nombre de la ubicación guardada, ej. `Monterrey, NL`) o, si no,
`lat` y `lon`. Con `municipio` se usa su punto de cultivo (ver "Ubicaciones" más abajo). La pantalla
de Suelo usa la ubicación que eligió el agricultor en el selector de arriba.

| Ruta | Parámetros extra | Devuelve | Sección |
|---|---|---|---|
| `GET /api/suelo/actual` | — | Humedad (superficie, raíz, perfil) y temperatura del suelo del último día con datos | 2, 3 |
| `GET /api/suelo/estado` | — | Humedad vs. otros años en esta época (percentil SMAP) | 1 |
| `GET /api/suelo/historico` | `anio_inicio`, `anio_fin` | Serie mensual de humedad, temperatura y evaporación | 4, 8 |
| `GET /api/suelo/propiedades` | — | pH, arcilla, arena, limo, carbono orgánico y textura | 5 |
| `GET /api/suelo/erosion` | — | Pendiente (SRTM) con su clase FAO, factor LS y días de lluvia muy intensa | 6 |
| `GET /api/suelo/agua-subterranea` | — | Tendencia de GRACE en la región | 7 |
| `GET /api/suelo/smap` | — | Humedad superficial medida por SMAP, últimos días | 2 |
| `GET /api/suelo/raiz` | — | Humedad de la zona de raíces (SMAP L4) | 2 |
| `GET /api/suelo/retencion` | — | Cuánto sube y qué tan rápido baja la humedad con la lluvia (SMAP + POWER) | 2 |
| `GET /api/suelo/cobertura` | — | NDVI de MODIS: promedio por mes, meses de suelo desnudo y último valor | 9 |
| `GET /api/suelo/proyeccion` | — | Últimos días reales de POWER y la estimación de hoy a +6 días (humedad de raíz, temperatura, pérdida de agua, lluvia), con resumen, aviso de lluvia fuerte y los supuestos usados (caché de 3 h) | 11 |
| `GET /api/suelo/resumen` | — | Todo lo anterior ya clasificado, en una sola respuesta (ver "Para el Planificador") | todas |

## Variables por fuente

| Fuente | Variables | Notas |
|---|---|---|
| NASA POWER | `GWETTOP`, `GWETROOT`, `GWETPROF`, `TS`, `PRECTOTCORR` | Sin llave. Humedad viene de 0 a 1. `-999` = sin dato. ~50 km de resolución |
| SoilGrids | `phh2o`, `clay`, `sand`, `silt`, `soc` (capas 0–5 y 5–15 cm) | Sin llave. Valores escalados (pH ×10, arcilla en g/kg). Da `null` en zonas urbanas |
| SRTM (SRTMGL1, 30 m) | Elevación → pendiente | Pide el token de Earthdata. Se baja el mosaico de 1°×1° la primera vez |
| GRACE / GRACE-FO | Anomalía de almacenamiento de agua | Pide el token de Earthdata. Resolución muy gruesa (cientos de km): solo tendencia regional |
| SMAP (L3 y L4) | Humedad superficial y de raíz | Pide el token de Earthdata |
| MODIS | NDVI (MOD13) y cobertura del suelo (MCD12Q1) | Pide el token de Earthdata |

Open-Meteo e IMERG se consideraron al inicio y no se usan en Suelo: la lluvia sale de NASA POWER.

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
- **Proyección a 7 días** (`services/suelo/proyeccion.py`): balance de agua diario, el planteamiento de la FAO
  (boletín 56, Allen et al. 1998): `almacén = almacén anterior + lluvia − pérdida`. Parte del último dato real de POWER
  (llega con 2-3 días de retraso) y avanza con el pronóstico de Open-Meteo.
  - El almacén es la zona de raíz de POWER (0-100 cm, % de saturación) pasada a mm con **1 000 mm × 45 % de poros =
    450 mm**. Contra los datos de POWER (≈ 30 mm de lluvia suben la humedad ≈ 5 puntos) el orden de magnitud coincide.
  - La pérdida es la evapotranspiración de referencia del pronóstico (`et0_fao_evapotranspiration`, FAO Penman-Monteith)
    por un factor **calibrado con los últimos 7 días del mismo punto** (evaporación real `EVLAND` de POWER entre ET0), con
    tope de 0.2 a 1.5; sin calibración, 0.6. Para Monterrey sale ≈ 0.67.
  - La temperatura del suelo es la de superficie (0 cm) de Open-Meteo, corregida con la diferencia promedio contra `TS`
    de POWER de esos días para que la curva continúe sin saltos.
  - Aviso de lluvia fuerte: un día de hoy en adelante con ≥ 20 mm (el mismo umbral R20mm que usa `/erosion`).
  - También aparece en "Show technical details" (`pages/Suelo/estimaciones.js`): la fila de estimación de la tarjeta de
    POWER; la humedad de raíz de **SMAP L4** continuada con línea punteada (a su último valor se le suma el mismo cambio
    de agua del balance, mm ÷ 10 = puntos de volumen); y la gráfica de retención con la lluvia que POWER aún no trae
    (llenada con la de Open-Meteo) y la pronosticada, en barras claras con borde punteado. La humedad **superficial** de
    SMAP (5 cm) no se proyecta: cambia en horas y un balance diario no es confiable ahí.
  - Las tarjetas de largo plazo **no llevan pronóstico**, solo lo que cada dato permite sin inventar, y así se rotula:
    **Land and erosion** compara los días con lluvia ≥ 20 mm de esta semana (pronóstico) con los de un año típico (R20mm);
    **GRACE** prolonga 3 años, con línea punteada, la tendencia de toda la serie desde el último dato ("si sigue así": ≈ −20 cm
    en 5 años en Monterrey) y avisa si los últimos 5 años han ido más rápido; **la tendencia de humedad de 20 años**
    muestra el rango y el promedio típicos de cada uno de los próximos 6 meses (temporada seca y húmeda). NDVI y textura
    no cambian en una semana y no se tocaron.
  - **No se clasifica** ("hay que regar", "sequía"): no hay una regla oficial para eso con estos datos. Solo se dice si la
    humedad sube, baja o se mantiene (cambio de ±1 punto o menos = estable).
  - Límites: un punto de ~50 km, un suelo medio (no usa la textura de SoilGrids), sin escurrimiento ni drenaje y un
    pronóstico de lluvia que falla más mientras más lejos. Sirve para la tendencia, no para fechar un riego.
- **Textura**: clasificar arcilla/arena/limo con el triángulo de texturas (USDA).
- **Erosión**: no se calcula un "riesgo" propio; se dan la pendiente con su clase FAO y los días
  de lluvia ≥20 mm (R20mm).
- **Conversiones**: `-999` → `null`, pH ÷ 10, humedad 0–1 → %.

## Estado actual

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
| Calidad MODIS (`/cobertura`) | Solo píxeles con *pixel reliability* 0 (bueno) o 1 (marginal); se descartan nubes (3) y nieve (2) | Guía de usuario MOD13 (Didan et al., 2015) |
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
- Para llenarla con las ubicaciones guardadas de una vez (salta las que ya están):

  ```bash
  docker compose exec backend python -m scripts.generar_suelo_municipios
  ```
  Espera 13 s entre consultas para no pasar el límite (~2,470 municipios ≈ 9 horas; se guarda
  después de cada punto, así que se puede cortar y continuar).
- Trae las capas 0–5, 5–15 y 15–30 cm. Principal y el popup del cultivo del Planificador toman el pH de
  aquí mismo (`services/suelo_ubicacion.py`), así que todas las pantallas muestran la misma cifra.

## Ubicaciones: de dónde sale el punto de suelo

Suelo usa las **ubicaciones guardadas** del agricultor (tabla `ubicacion`, ver `backend/app/db.py` y
`services/ubicaciones.py`): las 4 ciudades de inicio, las que agregue con el buscador y "My location".
La pantalla manda el nombre de la ubicación elegida (`?municipio=Monterrey, NL`) y el backend:

1. Para **todas** las ubicaciones (las 4 de inicio y las que agregue el agricultor) busca **el píxel de
   cultivo más cercano** según el mapa de cobertura de NASA MODIS (MCD12Q1 v061, 500 m, clases IGBP 12
   "cultivo" y 14 "mosaico de cultivo"), a menos de ~50 km. Una consulta (~2 s); se guarda en
   `backend/data/suelo/cultivo_cercano.json`.
2. Si no hay cultivo cerca o MODIS no responde, usa las coordenadas del lugar.

No usa `lat_suelo`/`lon_suelo` de la tabla: al revisar los 4 puntos de inicio con MODIS, Pesquería (NL)
y Hunucmá (YUC) salen como pastizal y Arteaga (COAH) como matorral; solo el de Culiacán es cultivo. Principal,
las alertas y el popup del cultivo usan este mismo punto (`services/suelo_ubicacion.py`), así que sus cifras
coinciden con las de la pantalla Soil. Las columnas `lat_suelo`/`lon_suelo` de la tabla ya no se leen.

Se probó con las 32 capitales: el cultivo más cercano quedó a 1–10 km en casi todas (Baja California
Sur a ~47 km). Los datos ya descargados de esos puntos se quedan guardados, así que si el agricultor
agrega una capital, sale rápido.

**SMAP y las ciudades:** SMAP deja vacía la celda de 9 km cuando tiene mucha ciudad o agua. Si la celda
del punto no tiene ninguna medición en los últimos 10 días, se usa siempre la celda vecina con más
mediciones (~9 km); la respuesta lo indica con `celda_vecina: true`. Pasó en Monterrey, Puebla y Chetumal.

## Para el Planificador

Quien haga el Planificador **no necesita llamar a cada endpoint**: `GET /api/suelo/resumen?municipio=<nombre de la ubicación>`
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
- **Un punto por ubicación**: el cultivo más cercano al lugar (MODIS); no representa toda la región.
- `humedad_vs_normal` mide solo humedad del suelo: **no es sequía oficial** (en algunos estados del sur
  SMAP marca más seco que el Monitor de Sequía de CONAGUA).
- SMAP marca muchas mediciones como "calidad no recomendada" (vegetación densa, interferencia).
- GRACE es regional (~300 km) y mide agua total, no solo la subterránea.

## Archivos

| Capa | Archivo |
|---|---|
| Router | `backend/app/routers/suelo/endpoints.py` |
| Servicios | `backend/app/services/suelo/`: `nasa_power.py`, `soilgrids.py`, `srtm.py`, `grace.py`, `smap.py` (L3 y L4), `modis.py`, `puntos.py` (punto de cultivo de cada ubicación) |
| Puente con otras pantallas | `backend/app/services/suelo_ubicacion.py`: pH, humedad y percentil de una ubicación, para Principal, el Planificador y las alertas |
| Scripts | `backend/scripts/`: `generar_suelo_municipios.py` (tabla SoilGrids) y `precargar_suelo.py` (SMAP, SRTM, MODIS), para las ubicaciones guardadas |
| Front (API) | `frontend/src/api/suelo.js` |
| Front (pantalla) | `frontend/src/pages/Suelo/`: `Suelo.jsx`, `Escala.jsx` y las gráficas, `resumen.js` (escalas y textos) y `Ayuda.jsx` (explicación de términos como "percentil") |

## Técnico

- Caché en memoria por (lat, lon, fechas): SoilGrids y POWER son lentos.
- Usar coordenadas de campo, no de centro de ciudad.
- Llaves de Earthdata (SMAP, IMERG, GRACE) en `.env`, nunca en el código.

## Por decidir con el equipo

1. ~~Principal y Clima muestran humedad del suelo: ¿llaman a `/api/suelo`?~~ Decidido: Principal ya usa el
   módulo Suelo (pH y humedad). Clima, cuando se haga, debería hacer lo mismo para no mostrar cifras distintas.
2. ~~Formato del semáforo para que lo use el Planificador.~~ Resuelto: `/api/suelo/resumen` ya trae todo clasificado.
3. ~~¿De dónde bajamos SRTM?~~ Decidido: SRTMGL1 (30 m) de LP DAAC con el token de Earthdata.
   Se baja el mosaico de 1°×1° la primera vez (~25 MB) y se guarda en `backend/data/srtm/`.
4. ~~¿GRACE e IMERG entran al MVP?~~ Decidido: **GRACE sí entra** (hay que crear cuenta de
   Earthdata). **IMERG se deja para después**; mientras, la lluvia sale de NASA POWER.
