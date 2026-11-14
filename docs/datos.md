# Catálogo de datos — Gestor maestro de cultivos

Reto: [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/).
Resumen del reto: herramienta de apoyo a decisiones que usa observaciones NASA + suelo local +
características de cultivos + prioridades del agricultor para **comparar al menos 3 estrategias de
rotación (incluida la actual)**, explicando por qué, con qué evidencia, riesgos y vacíos de información.
No reemplaza el criterio del agricultor.

Fuente: lista oficial de la pestaña Resources (leída 2026-11-14) + verificación propia de endpoints.
Versión en CSV para pegar en el Google Sheet del equipo: [datos.csv](datos.csv).

> **Nota:** no pude abrir el Google Sheet del equipo (requiere sesión). Antes de pegar, revisen que no
> dupliquemos filas que ya tengan.

## 1. Qué dato alimenta qué pantalla

| Pantalla (docx) | Datos | Fuente principal |
|---|---|---|
| Principal: temperatura 7 días + detalle de hoy | Pronóstico diario/horario | Open-Meteo (externo). NASA POWER solo trae histórico, no pronóstico |
| Ubicación | Geocodificación (nombre → lat/lon) | Open-Meteo Geocoding (externo) |
| Clima (por día) | Histórico diario: T, precipitación, humedad, radiación | **NASA POWER** (AG) + **GPM IMERG** para lluvia |
| Suelo (por día) | Humedad superficial y de zona radicular, temperatura de suelo; propiedades del suelo | **SMAP**, **POWER** (GWETROOT/GWETTOP), **GLDAS**; SoilGrids (externo) |
| Cultivos | Superficie, rendimiento y ciclo por cultivo y municipio; requisitos agroclimáticos | **SIAP Cierre Agrícola** (México) + FAO EcoCrop/GAEZ (externo) |
| Mercado | Precio medio rural histórico por cultivo/municipio; mayoreo diario | **SIAP** (histórico), **SNIIM** (mayoreo), FAOSTAT (contexto internacional) |
| Línea de tiempo | Calendario de rotación, periodos de campo desnudo, estrés | Landsat/MODIS/VIIRS (NDVI) + datos propios del usuario |

## 2. Datos NASA (prioridad para el reto)

| Dataset | Aporta | Resolución | Acceso | Prioridad |
|---|---|---|---|---|
| **NASA POWER** | Temp., precipitación, humedad, radiación, humedad de suelo (GWETROOT/GWETTOP), climatología mensual. Global | ~0.5° (≈50 km), diario desde 1981, retraso ~2-3 días | REST sin llave, JSON | **MVP** |
| **SMAP** | Humedad superficial y estado congelado/descongelado | 9-36 km (L3 SPL3SMP_E), cada 2-3 días | Earthdata (login gratis) vía CMR/`earthaccess` | MVP |
| **GPM IMERG** | Precipitación global, tasa y acumulados | 0.1°, 30 min / diario | Earthdata login; Worldview baja imágenes | MVP |
| **MODIS / VIIRS** | NDVI/EVI, estrés de vegetación, estacionalidad | 250 m–1 km | LP DAAC / AppEEARS (login) | MVP (NDVI) |
| **Landsat** | NDVI a escala de parcela, suelo desnudo | 30 m | EarthExplorer / STAC | Fase 2 |
| **ECOSTRESS** | Temperatura de superficie y evapotranspiración | ~70 m, revisita irregular | Earthdata | Fase 2 |
| **GLDAS / NLDAS** | Humedad de suelo, ET, T, lluvia en series continuas (NLDAS solo EE. UU.) | 0.25° (GLDAS) | Earthdata Search | Fase 2 |
| **SRTM** | Elevación, pendiente, erosión/escorrentía | 30 m | Earthdata | Fase 2 |
| **GRACE / GRACE-FO** | Tendencias de agua almacenada (mencionado en Objetivos) | ~300 km | Earthdata | Opcional |
| **GEDI L4** | Biomasa/dosel (útil sobre todo en zonas arboladas) | 25 m, muestreo | gedi.umd.edu | Opcional |

> **Qué está verificado y qué no:** de la tabla anterior, POWER lo probé yo (variables, unidades y
> cobertura) y SMAP solo en su catálogo. Las resoluciones de SMAP, IMERG, ECOSTRESS, GLDAS y GRACE
> son de referencia general y no las comprobé contra la ficha de cada producto; Landsat (30 m) y
> MODIS/VIIRS (250–1000 m) sí vienen del texto del reto.

## 3. Datos externos recomendados

| Dataset | Aporta | Cobertura | Acceso | Prioridad |
|---|---|---|---|---|
| **Open-Meteo** (forecast + geocoding) | Pronóstico 7 días, ET0, humedad/temperatura de suelo horaria, búsqueda de ciudades | Global | REST sin llave | **MVP** |
| **SoilGrids (ISRIC)** | pH, carbono orgánico, arcilla/arena/limo por profundidad | Global, 250 m | REST sin llave (no probé límites de uso) | **MVP** |
| **FAO EcoCrop / GAEZ** | Rangos de T, lluvia, pH y ciclo por cultivo; idoneidad agroclimática | Global | Descarga en gaez.fao.org | MVP (tabla de cultivos) |
| **FAOSTAT Precios al productor** | Precios anuales (desde 1991) y mensuales (desde 2010) por país | 193 países | Bulk CSV/ZIP o API | MVP (mercado) |
| **World Bank Pink Sheet** | Precios internacionales mensuales de commodities | Global | Excel mensual (formato sin verificar) | Fase 2 |
| **ERA5 (Copernicus)** | Reanálisis horario; relleno donde faltan estaciones | Global | CDS API (cuenta gratis) | Fase 2 |
| **Sentinel-2 (ESA)** | Imágenes 10-20 m con red-edge, NDVI de parcela | Global | Copernicus Data Space | Fase 2 |
| **OpenET** | ET a escala de parcela | Oeste de EE. UU. | API con llave | Solo si el caso es EE. UU. |

## 3b. México (cobertura principal)

Los datasets NASA y Open-Meteo/SoilGrids/FAO son globales y sirven tal cual. Lo que el reto lista de
USDA no cubre México, así que estas son las fuentes locales equivalentes:

| Dataset | Aporta | Acceso | Equivale a | Prioridad |
|---|---|---|---|---|
| **SIAP — Cierre de la Producción Agrícola** | Por **municipio**, cultivo, ciclo (Otoño-Invierno / Primavera-Verano / Perennes) y modalidad (riego / temporal): superficie sembrada, cosechada y siniestrada, volumen, rendimiento, **precio medio rural** y valor. 1980–2025 | CSV directo, sin login, un archivo por año (~6 MB, ~37 mil filas en 2024), codificación ISO-8859-1 | CDL + QuickStats + precios al productor | **MVP** |
| **SMN/CONAGUA — pronóstico municipal** | `method=1`: **4 días**, diario, por municipio (2 463 municipios): Tmax, Tmin, precipitación (l/m²), prob. de lluvia, nubosidad (`cc` = cobertura de nubes %), viento y descripción del cielo. `method=3`: pronóstico **por hora** con temperatura y humedad relativa (`hr`), ~7.5 MB | `smn.conagua.gob.mx/tools/GUI/webservices/?method=1` (gzip, ~330 KB) y `?method=3`; sin llave. Campos según la [documentación oficial](https://smn.conagua.gob.mx/es/web-service-api) | Alternativa oficial a Open-Meteo, pero solo 4 días: para los 7 días de la pantalla principal hace falta Open-Meteo | MVP (opcional) |
| **SNIIM (Secretaría de Economía)** | Precios de mayoreo diarios: frutas y hortalizas, granos, azúcar, aceites, insumos, flores | Consultas web y anuarios HTML; **no hay API documentada** | AMS Market News | Fase 2 (requiere scraping) |
| **INEGI Edafología 1:250 000** | Tipos de suelo y erosión (cartografía vectorial) | Descarga de shapefiles en inegi.org.mx | SSURGO / Web Soil Survey | Fase 2. SoilGrids cubre el MVP |
| **INEGI Uso de suelo y vegetación** | Cobertura/uso de suelo | Descarga de shapefiles | NLCD | Fase 2 |
| **SIAP Avance agrícola / Fronteras agrícolas** | Avance de siembra y cosecha del año en curso | nube.agricultura.gob.mx | — | Opcional |

**Qué da SIAP y por qué es la pieza central:** una sola fuente alimenta las pantallas de Cultivos y
Mercado y la línea de tiempo (el ciclo agrícola y riego/temporal son justo el vocabulario de rotación).
Además deja calcular, por municipio, qué se siembra hoy (la rotación "actual" que pide el reto) y
comparar rendimientos y precios de alternativas.

## 3c. Estados fronterizos de EE. UU. (CA, AZ, NM, TX)

Open-Meteo, POWER, SoilGrids, SMAP, IMERG y MODIS funcionan igual en esos estados. Solo para suelo,
cultivos y precios se necesitan fuentes USDA:

| Dataset | Aporta | Acceso | Nota |
|---|---|---|---|
| **USDA NASS QuickStats** | Rendimiento, superficie y producción por condado | API con llave gratis | Sin llave responde 401 |
| **CDL / CropScape** | Cultivo sembrado por píxel de 30 m, anual | Servicio web y descarga | Mi consulta de prueba al servicio salió vacía; falta revisar si estaba caído |
| **Web Soil Survey / SSURGO** | Suelo detallado | Web / API | Sustituto de INEGI + SoilGrids |
| **AMS Market News (MARS)** | Precios de mayoreo | API | Responde 403 sin credenciales |
| **PRISM** | Climatología | Descarga | Opcional |

Recomendación: tratar EE. UU. como "fase 2" y diseñar la capa de datos con una interfaz por país
(`ProveedorCultivos`, `ProveedorPrecios`) para que SIAP y NASS sean intercambiables.

## 4. Verificado hoy (2026-11-14)

| Prueba | Resultado |
|---|---|
| POWER diario, punto (CDMX), 8 variables AG | OK, sin llave |
| POWER climatología mensual (Culiacán) | OK |
| POWER últimos días | Devuelve `-999` (sin dato) en los 3 días más recientes → tratar `-999` como nulo |
| Open-Meteo forecast con humedad/temp. de suelo | OK, sin llave |
| Open-Meteo geocoding (`Culiacan`) | OK, devuelve lat/lon/zona horaria |
| SoilGrids en parcela rural (Sinaloa) | OK (pH, arcilla, SOC) |
| SoilGrids en punto urbano (CDMX) | `null` — está enmascarado; hay que elegir puntos agrícolas |
| NASA CMR (metadatos SMAP L3) | OK, sin llave |
| FAOSTAT bulk, World Bank Pink Sheet | Responden 200; formato de archivo sin revisar |
| **SIAP Cierre Agrícola 2024 (CSV)** | OK: 36 992 filas, 24 columnas, sin login; trae precio medio rural |
| SMN pronóstico municipal (`method=1`) | OK: JSON en gzip, 9 852 registros = 2 463 municipios × 4 días; trae Tmax/Tmin, lluvia, prob. de lluvia, nubosidad y viento. **No trae humedad** |
| SMN pronóstico por hora (`method=3`) | OK: ~7.5 MB; trae temperatura y humedad relativa (`hr`). No revisé cuántas horas cubre |
| SNIIM (sitio principal) | Responde; solo páginas web, sin API |
| `datos.gob.mx` (API CKAN) | **403 Access Denied** desde mi equipo; usar los CSV directos de SIAP |
| INEGI API de indicadores | 403 (requiere token); no probé la descarga de shapefiles |
| USDA NASS QuickStats / AMS MARS | 401 / 403 sin llave |
| CropScape (CDL) | Respuesta vacía en mi prueba |

## 5. Riesgos y decisiones abiertas

1. **Foco México, frontera EE. UU. como extra.** SIAP reemplaza a CDL/QuickStats en México. Los
   municipios y los nombres de cultivo de SIAP no coinciden con los de EcoCrop/FAO: hará falta una
   tabla de equivalencias hecha a mano (p. ej. "Maíz grano" ↔ *Zea mays*).
   SIAP tiene un rezago anual (cifras definitivas de 2025 ya publicadas) y trae precios del
   **productor**, no del mayoreo.
2. **Resolución gruesa de POWER/SMAP** (decenas de km): sirve para tendencias regionales, no para una
   parcela. Hay que decirlo en la UI (el reto pide explicar satélite vs. mediciones en tierra).
3. **Earthdata login** es necesario para SMAP, IMERG, MODIS y ECOSTRESS. Guardar el token en `.env`,
   nunca en el repo.
4. **Precios en tiempo real**: FAOSTAT es anual/mensual con rezago; para "fluctuaciones" sirve como
   serie histórica, no como cotización diaria.
5. **Profundidad de GWETROOT**: la documentación de POWER y la de MERRA-2 no coinciden (200 cm vs.
   0-100 cm); citarlo como "zona radicular" sin fijar cifra.
6. **Pronóstico**: POWER no lo da; si quieren quedarse 100 % NASA para la pantalla principal, hay que
   mostrar solo histórico reciente.

## 6. Propuesta de MVP

POWER + Open-Meteo (o SMN) + SoilGrids + **SIAP** + EcoCrop cubren las seis pantallas sin login.
Después añadir SMAP/IMERG y NDVI de MODIS para tener narrativa NASA fuerte y comparar las 3
rotaciones; luego SNIIM (mayoreo), INEGI (suelo) y el módulo de estados fronterizos.

Orden sugerido: (1) cargar SIAP 2015-2025 a SQLite/Parquet, (2) endpoint de clima con POWER +
Open-Meteo, (3) SoilGrids por coordenada, (4) tabla de cultivos SIAP↔EcoCrop, (5) NDVI y SMAP.

## 7. Búsqueda de datos pendientes (2026-11-14)

Resultado de buscar los vacíos de la sección 5 y del análisis anterior. Lo marcado "probado" lo
descargué o consulté yo.

| Pendiente | Qué encontré | Estado |
|---|---|---|
| **Requisitos por cultivo** | [EcoCrop_DB.csv](https://github.com/OpenCLIM/ecocrop) (copia de la base FAO, 2 568 especies, 1.6 MB): temperatura óptima y límite (`TOPMN/TOPMX/TMIN/TMAX`), lluvia anual (`ROPMN/ROPMX/RMIN/RMAX`), pH, drenaje, textura, salinidad, temperatura letal (`KTMP`) y **ciclo en días (`GMIN/GMAX`)**. Trae maíz, frijol, sorgo, trigo, garbanzo, alfalfa, soya, chile, avena, cebada y cártamo. El jitomate está como *Lycopersicon esculentum*. Maíz: temp. óptima 18–33 °C, lluvia 600–1200 mm, pH 5–7, ciclo 65–365 días | Probado. El repo usa licencia OGL v3; los datos originales son de FAO, hay que citar. Algunas especies tienen varias filas y pH en `NA` |
| **Fijación de nitrógeno** | No hay tabla lista. EcoCrop trae la familia (`FAMNAME`); las leguminosas (*Leguminosae/Fabaceae*, 514 filas) fijan nitrógeno | Heurística por familia, a validar con un agrónomo |
| **Profundidad de raíz y uso de agua** | FAO-56 [Tabla 22](https://www.fao.org/3/x0490e/x0490e0e.htm): profundidad máxima de raíz y fracción de agotamiento (maíz 1.0–1.7 m, p=0.55; alfalfa 1.0–2.0 m; sorgo 1.0–2.0 m; garbanzo 0.6–1.0 m; soya 0.6–1.3 m; jitomate 0.7–1.5 m). [Tabla 12](https://www.fao.org/3/x0490e/x0490e0b.htm): coeficientes Kc | Las tablas están en HTML; hay que transcribirlas a CSV. No verifiqué los términos de reúso de FAO |
| **Efecto de cada rotación (plagas, enfermedades, nutrientes)** | No encontré ningún dataset | Sigue siendo conocimiento a curar a mano |
| **Estaciones en tierra** | SMN publica un `.txt` por estación con precipitación, evaporación, Tmax y Tmin **diarios** desde el primer dato (Aguascalientes desde 1878), más normales 1961–90, 1971–2000 y 1981–2010. Hay un catálogo por estado: Aguascalientes 73 estaciones, Sinaloa 173. Patrón: `.../Normales_Climatologicas/Diarios/<estado>/dia<clave>.txt` | Probado en Ags y Sin. Faltantes marcados `NULO`. Hay estaciones "operando" con datos que se cortan (Acatitán: último dato 2026-04-28) |
| **Agua para riego** | SIAP publica 85 distritos de riego (polígonos con superficie y presas) en un servicio ArcGIS REST abierto. La app de presas agrícolas usa un `grafica.php` que no probé | Distritos probados (count=85) |
| **Calendario de siembra y cosecha** | El calendario de SIAP es agregado por ciclo (OI/PV), no por cultivo. El "Avance mensual" cubre 64 cultivos por municipio, pero es una app web y no encontré CSV | Parcial. La ventana de siembra por cultivo no está como dato descargable |
| **Plagas y enfermedades** | SENASICA tiene SIRVEF (guías de síntomas y daños), `sinavef` redirige ahí. No encontré descarga abierta de datos de plagas | No resuelto |
| **Precios de mayoreo** | SNIIM es un formulario ASP.NET sin API. Se necesitaría un scraper que envíe el formulario | Sin cambios; fase 2 |

Lo que queda realmente abierto: efecto de cada rotación sobre plagas y nutrientes, ventanas de siembra
por cultivo, y datos de plagas.
