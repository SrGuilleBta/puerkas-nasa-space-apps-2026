# Pipeline de Cultivos

Alimenta la pantalla **Cultivos** (enciclopedia de cultivos con viabilidad por municipio o estado).
Precalcula todos los indicadores y los guarda en JSON; la API solo lee esos archivos. No se llama a
ninguna API externa en tiempo de consulta.

```
backend/data/siap/*.csv ───────┐
backend/data/sequia/*.xlsx ────┤     python -m pipeline.cultivos      backend/data/cultivos/*.json
backend/data/ecocrop/*.csv ────┼──────────────────────────────────▶   (no se commitea)
backend/data/inflacion/*.csv ──┤                                              │
backend/pipeline/cultivos/curado.json ─┘                                      ▼
                                                                  /api/cultivos/... (app/services/cultivos.py)
```

## Cómo correrla

| Situación | Qué hacer |
|---|---|
| Con Docker (lo normal) | Nada: el contenedor `backend` corre la pipeline al arrancar si falta `data/cultivos/meta.json` (~1 min la primera vez). |
| Regenerar tras cambiar código o datos | `docker compose run --rm backend sh -c "pip install -r requirements.txt -r pipeline/requirements.txt && python -m pipeline.cultivos"` y luego `docker compose restart backend` (la API guarda los JSON en memoria). |
| Sin Docker | Desde `backend/`: `pip install -r pipeline/requirements.txt` y `python -m pipeline.cultivos` |
| Actualizar las fuentes | `python -m pipeline.cultivos descargar` (Monitor de Sequía, EcoCrop, inflación) |
| Imagen de producción | El `Dockerfile` la genera en una etapa del build. |

Los parámetros (ventana de años, año base de precios, umbrales de sequía) están todos en
[backend/pipeline/cultivos/config.py](../backend/pipeline/cultivos/config.py).

## Fuentes

| Fuente | Archivo | Para qué |
|---|---|---|
| SIAP Cierre de la Producción Agrícola 2015–2025 | `data/siap/` | Rendimiento, precio, superficie, siniestro, riego/temporal, ciclos |
| Monitor de Sequía de México (CONAGUA/SMN) | `data/sequia/MunicipiosSequia.xlsx` | Categoría D0–D4 por municipio, quincenal desde 2003 (corte actual: 2026-10-31) |
| FAO EcoCrop (tabla de [OpenCLIM/ecocrop](https://github.com/OpenCLIM/ecocrop)) | `data/ecocrop/EcoCrop_DB.csv` | Rangos de temperatura, lluvia y pH, ciclo, familia, tolerancia a mal drenaje |
| FMI WEO, inflación promedio anual de México | `data/inflacion/inflacion_mexico.csv` | Deflactar el precio medio rural a pesos de 2025 |
| Curado a mano | `pipeline/cultivos/curado.json` | Tipo, familia, fijación de N, ciclo realista, descripción, suelo y cuidados |

**Inflación:** la API del INEGI pide token, así que se usa la inflación promedio anual del FMI, que
equivale a la variación del INPC promedio anual. Donde se traslapa con la serie de la OCDE (el mismo
INPC), coincide al décimo. El FMI a veces responde 403 a clientes que no son navegador; si
`descargar` falla, se conserva el CSV del repo y basta con agregar a mano la fila del año nuevo.

## Decisiones tomadas (las "pendientes" del documento de fuentes)

| Pendiente | Decisión | Dónde cambiarla |
|---|---|---|
| Ventana para la mediana | 10 años (2016–2025) | `VENTANA_ANIOS` |
| Año base para deflactar el PMR | 2025 | `ANIO_BASE_PRECIOS` |
| GAEZ v4 vs v5 | **Sin hacer.** Los campos `gaez.*` salen `null` con `estado: "pendiente"` | — |
| Score único de viabilidad | No se calcula: se entregan los indicadores por separado y en etiquetas | — |

## Limpieza de SIAP (en `fuentes.py`)

- Codificación ISO-8859-1. Las columnas se asignan **por posición** porque 2015–2020 cambian dos nombres.
- 2021 y 2022 traen algunos números con separador de miles (`"10,271"`).
- `Idmunicipio` de SIAP **es la clave municipal de INEGI** (verificado con Baja California, incluido
  San Quintín = 02006). CVEGEO = `Idestado` (2 dígitos) + `Idmunicipio` (3 dígitos).
- Un municipio puede venir partido en varios CADER (unas 1,000 llaves repetidas al año). Se suman
  superficie, volumen y valor; **rendimiento y precio se recalculan** como cocientes ponderados
  (`volumen / cosechada`, `valor / volumen`). Las columnas `Rendimiento` y `Preciomediorural` del CSV no se usan.
- Id de cultivo = slug del nombre (`maiz-grano`). Si un nombre aparece en varias unidades (flores en
  gruesa y en planta), la unidad entra en el id.
- 2020 y 2021 tienen unas 28 mil filas contra ~37 mil de los demás años. Así viene de SIAP.

## Indicadores

Se calculan a nivel **municipio, estado y nacional** con el mismo código, en dos granularidades:
por `(cultivo, ciclo, modalidad)` —la llave del documento de fuentes— y por cultivo (sumando ciclos y modalidades).

| Indicador | Cálculo |
|---|---|
| Rendimiento p25/p50/p75 | Percentiles del rendimiento anual (`volumen / cosechada`) en la ventana, **de esa ubicación**. Con menos de 3 años solo hay p50. |
| CV del rendimiento | `desv. estándar / media` del rendimiento anual (mínimo 3 años) |
| Precio real | `valor / volumen` de cada año × deflactor a pesos de 2025. Se da la mediana, el último año y el nominal del último año. |
| Ingreso por ha sembrada | `valor real / superficie sembrada`, mediana anual. Al dividir entre lo **sembrado** ya descuenta las pérdidas por siniestro. |
| Rentabilidad | Percentil del ingreso por ha entre los cultivos de la misma ubicación (≥ 0.75 alta, ≤ 0.25 baja) |
| Tasa de siniestro | `Σ siniestrada / Σ sembrada` en la ventana |
| Sensibilidad a sequía | Tasa de siniestro en temporadas **con sequía severa** contra temporadas normales (ver abajo). `alta` si la diferencia es ≥ 10 puntos o la tasa en sequía ≥ 25%; `media` si es ≥ 3 puntos; `baja` en otro caso; `sin_evidencia` si hay menos de 1 temporada con sequía o menos de 2 normales. |
| Riesgo hídrico | `0.25·amenaza + 0.75·exposición·(0.5 + 0.5·vulnerabilidad)`. Amenaza = frecuencia de lecturas D2+ en la zona (saturada en 30%); exposición = proporción en temporal; vulnerabilidad = CV del rendimiento en temporal (saturado en 0.4). Niveles: < 0.33 bajo, < 0.6 medio, si no alto. |
| Sensibilidad a inundación | Por ahora solo EcoCrop: si el cultivo tolera suelos mal drenados. **Falta el Atlas Nacional de Riesgos (CENAPRED).** |
| Reparto por ciclo | Proporción de la superficie en O-I, P-V y perennes. Sirve para "siembra ideal" según lo que se practica en la zona. |

**Temporada con sequía severa:** para cada año y ciclo se toman las lecturas del Monitor dentro de la
temporada (O-I: octubre del año anterior a mayo; P-V: abril a noviembre; perennes: todo el año). En
un municipio cuenta como temporada con sequía si al menos el 25% de las lecturas fue D2 o peor. En
un estado o a nivel nacional, si al menos el 30% de sus municipios la tuvo.

### Rotación practicada (`rotacion.py`)

SIAP no sigue parcelas, así que esto es una aproximación: que el cultivo B se siembre en el **ciclo
opuesto** (O-I ↔ P-V) al de A, en el mismo municipio y año.

- `frecuencia` = proporción de años (o municipios-año, en estado y nación) con A en que también hubo B en el ciclo opuesto.
- `area_relativa` = superficie de B en ese ciclo / superficie de A, con tope de 1. Sin esto, en
  municipios grandes como Ahome todo coexistía con todo al 100%.
- `practica` = Σ por ciclo de A de `peso del ciclo × frecuencia × √area_relativa`. El peso es la
  proporción de la superficie de A en ese ciclo, para que el 4% de frijol de P-V en Ahome no domine.
- `afinidad` = 0.5·practica + 0.5·agronomía. La agronomía parte de 0.5: +0.2 si son de familia
  distinta, −0.35 si son de la misma familia, +0.3 si B es leguminosa y A no; un monocultivo vale 0.1.
- Se descartan socios con `practica` < 0.03 y se guardan los 5 mejores. Si el municipio no tiene
  ninguno, se usan los del estado (`nivel_datos: "estado"`). Los perennes no llevan rotación.

## Salida (`backend/data/cultivos/`)

| Archivo | Contenido |
|---|---|
| `catalogo.json` | Ficha estática de los 399 cultivos con registros: nombre científico, tipo, familia, ciclo en días, agua, temperatura, pH, tolerancia a encharcamiento, descripción, suelo, cuidados y resumen nacional |
| `ubicaciones.json` | 32 estados con sus municipios (lista INEGI del Monitor más los de SIAP) y `con_datos` |
| `municipios/{CVEGEO}.json` | Indicadores de cada cultivo sembrado en el municipio (unos 2,450 archivos) |
| `estados/{CVE_ENT}.json`, `nacional.json` | Lo mismo agregado por estado y para todo el país |
| `meta.json` | Fecha de generación, ventana y fuentes |

Un archivo de ubicación (abreviado):

```jsonc
{
  "ubicacion": {"nivel": "municipio", "clave": "32010", "nombre": "Fresnillo", "cve_ent": "32", "estado": "Zacatecas"},
  "ventana": [2016, 2025],
  "contexto": {"superficie_sembrada_prom_ha": 157089.2, "pct_riego": 0.29, "n_cultivos": 43,
               "sequia": {"frec_d1": 0.35, "frec_d2": 0.13, "categoria_actual": -1, "fecha": "2026-10-31"}},
  "cultivos": [{
    "id": "frijol", "nombre": "Frijol", "n_anios": 10, "anio_ultimo": 2025,
    "rendimiento": {"p25": 0.61, "p50": 0.64, "p75": 0.85, "cv": 0.21, "unidad": "t/ha"},
    "precio": {"pmr_real_p50": 18788, "pmr_real_ultimo": 17051, "pmr_nominal_ultimo": 17051, "unidad": "$/t", "anio_base": 2025},
    "rentabilidad": {"ingreso_ha_real_p50": 12177, "percentil_zona": 0.08, "nivel": "baja"},
    "siniestro": {"tasa": 0.048, "tasa_sequia": 0.086, "tasa_normal": 0.033, "n_temporadas_sequia": 3, "n_temporadas_normales": 7},
    "sensibilidad_sequia": "media",
    "riesgo_hidrico": {"score": 0.68, "nivel": "alto", "pct_riego": 0.09, "cv_rendimiento_temporal": 0.27},
    "ciclos": {"PV": 1.0}, "ciclo_principal": "PV",
    "por_ciclo_modalidad": [{"ciclo": "PV", "modalidad": "temporal", "rend_p50": 0.49, "...": "..."}],
    "rotacion": {"nivel_datos": "municipio", "socios": [{"socio_id": "avena-forrajera-en-verde", "practica": 0.12, "afinidad": 0.41, "razones": ["..."]}]},
    "etiquetas": [{"tipo": "negativa", "titulo": "Riesgo hídrico alto", "detalle": "Depende de la lluvia y su rendimiento varía mucho"}],
    "situacion_actual": [{"tipo": "alerta", "titulo": "Precio por debajo del promedio", "detalle": "El precio medio rural de 2025 fue 9% menor que la mediana 2016–2024 (pesos de 2025)"}],
    "gaez": {"estado": "pendiente"}
  }]
}
```

Los valores `null` se omiten para que los archivos pesen menos: el frontend debe tratar una llave
ausente como "sin dato".

`etiquetas` corresponde a los chips de la ficha del Figma ("Alta rentabilidad", "Rotación favorable",
"Sensible a sequía") y `situacion_actual` a "Para tu situación actual". Ya vienen con su texto.

## API

| Ruta | Para qué |
|---|---|
| `GET /api/cultivos/biblioteca?clave=&buscar=` | Barra lateral. Con `clave`, ordena por superficie local y marca `sembrado_en_ubicacion`. La búsqueda no distingue acentos. |
| `GET /api/cultivos/viabilidad?clave=&cultivo=` | **Ficha principal.** Junta catálogo e indicadores. Si el municipio no siembra el cultivo, cae al estado y luego a la nación; `nivel_datos` y `sembrado_en_ubicacion` lo indican. |
| `GET /api/cultivos/ubicacion?clave=` | Todos los cultivos de una ubicación |
| `GET /api/cultivos/catalogo` | Catálogo completo |
| `GET /api/cultivos/ubicaciones` | Selector de estado y municipio |
| `GET /api/cultivos/meta` | Fecha de generación y fuentes |

`clave`: `00` nacional, 2 dígitos estado, 5 dígitos municipio (CVEGEO). Ejemplos:
`/api/cultivos/viabilidad?clave=25001&cultivo=maiz-grano` (Ahome, Sin.) y
`/api/cultivos/viabilidad?clave=19039&cultivo=maiz-grano` (Monterrey: no tiene registros
agrícolas, así que responde con los datos de Nuevo León).

## Limitaciones y pendientes

1. **GAEZ** (idoneidad biofísica y brecha de rendimiento): requiere bajar los rásters de S3 y hacer
   estadística zonal contra el Marco Geoestadístico del INEGI (geopandas y rasterio). Va en una etapa nueva.
2. **CENAPRED** para inundación y **disponibilidad de acuíferos** (DOF) para el riesgo hídrico de los cultivos de riego.
3. **Textos de manejo**: `curado.json` tiene descripción y cuidados para 22 cultivos. Son un
   borrador general (`texto_revisado: false`); hay que revisarlos contra las fichas del INIFAP.
   Los demás cultivos solo tienen datos de EcoCrop o ninguno.
4. **SIAP no distingue variedades** ("Maíz grano", no "Maíz amarillo"; "Frijol", no "Frijol pinto").
   La biblioteca del Figma tendrá que usar los nombres de SIAP.
5. El **precio medio rural** es precio al productor, promedio anual. No sirve como precio de mercado diario.
6. La rotación es co-ocurrencia municipal, no seguimiento de parcelas.
7. Los municipios sin registros en SIAP (urbanos como Monterrey) no tienen archivo propio ni `contexto`.
