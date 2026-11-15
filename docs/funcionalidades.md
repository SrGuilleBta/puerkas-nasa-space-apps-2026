# Qué hará cada parte del sistema (v1, borrador)

Basado en el prototipo de Figma ("CroPro", [enlace en el README](../README.md)). Lo leí recorriendo
las pantallas de la vista previa el 2026-11-14; no tengo acceso al código del Figma. **Los números,
fechas y nombres del Figma son ejemplos** (todo aparece en junio de 2025 con datos inventados): lo
que importa es qué muestra cada pieza, no el valor.

Para cada pantalla: qué muestra, de dónde saldría cada dato (fuentes en [datos.md](datos.md)) y si
el dato está **resuelto**, **parcial** o **falta**. Es un punto de partida para mejorarlo.

**Avance (2026-11-15):** **Principal**, **Planificador**, **Noticias** y **Suelo** ya están implementados con datos
reales (clima de Meteomatics, suelo de NASA y SoilGrids, planes en SQLite, feeds de CIMMYT y NASA). **Clima** y
**Mercado** siguen pendientes; de **Cultivos** ya están el catálogo y la API (`/api/cultivos`) y falta su pantalla.
Donde la tabla dice "Implementado" ya funciona en la aplicación.

## Piezas compartidas (en todas las pantallas)

| Pieza | Qué hace | Dato / fuente | Estado |
|---|---|---|---|
| Selector de **ubicación** (arriba) | Elige dónde estás. Trae 4 ciudades de inicio (Monterrey, Saltillo, Culiacán, Mérida); se pueden **agregar lugares de México** buscándolos por nombre, **usar mi ubicación** (GPS del navegador, se guarda como "Mi ubicación") y quitar los que sobren (siempre debe quedar uno). Todo lo demás se recalcula para ese lugar | Tabla `ubicacion` en SQLite; búsqueda por nombre con el geocodificador de Open-Meteo limitado a México (`countryCode=MX`). Falta ligar cada lugar con el municipio de SIAP | **Implementado**; la equivalencia con SIAP hay que armarla |
| "Datos actualizados 09:42" | Hora de la última consulta | La marca el backend al responder | Resuelto |
| Menú lateral | Principal, Clima, Mercado, Cultivos, Planificador, Noticias | Solo navegación | Resuelto |
| **Plan activo** (abajo del menú) | Muestra el plan que se está viendo en el Planificador: nombre, número de parcelas y hectáreas totales. Se vuelve a consultar cada vez que se abre el menú | `GET /api/planificador/planes` y `/planes/{id}` (componente `PlanLateral`) | **Implementado** |

## 1. Principal

Resumen de todo en una pantalla.

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| **Banner de alertas** (clima, plagas y enfermedades) | Reglas sobre el pronóstico de Meteomatics y los cultivos en curso del plan (`services/alertas.py`, `GET /api/principal/alertas`). Helada y calor se miden contra lo que **tolera cada cultivo en curso** (rango de temperatura del catálogo; con un margen de 3 °C para avisar antes) y, sin ficha, con umbrales generales. También avisa **falta de lluvia** (la lluvia observada de los últimos 30 días de NASA POWER contra lo que necesita cada cultivo por día; avisa que se puede regar), **riesgo de encharcamiento** (lluvia fuerte con cultivos sensibles), lluvia fuerte y viento, y "condiciones favorables" para hongos (roya, tizón), pulgón/mosca blanca/araña roja y gusano cogollero. Son avisos para revisar el campo, no detecciones; los umbrales son generales y se afinarán con el catálogo de Cultivos. Alcance: hoy y los 6 días siguientes | **Implementado** |
| **Pronóstico de 7 días**: desde hoy y los 6 siguientes, con temperatura y % de lluvia | Meteomatics (Tmax/Tmin, probabilidad de lluvia, símbolo del cielo), con caché de 10 minutos | **Implementado** |
| **Condiciones de hoy**: temperatura, sensación térmica, cielo, "óptimo para campo", humedad, viento, humedad del suelo, pH del suelo | Meteomatics (clima) y el módulo Suelo (pH de SoilGrids y humedad de la raíz de NASA POWER, del cultivo más cercano según MODIS; las mismas cifras de la pantalla Soil; si tardan más de 6 s la humedad queda con la de Meteomatics y el pH vacío, y quedan en caché). "Óptimo para campo" es una regla nuestra | **Implementado** |
| **Alerta regional** (ej. huracán, Protección Civil) | No hay una API oficial de alertas que funcione. La tarjeta ahora muestra el **último titular de Noticias** (una externa si hay, si no un aviso propio) y lleva a esa pantalla; si Noticias falla, no aparece | **Implementado** (como "Latest news"); alertas oficiales siguen faltando |
| **Cultivos activos**: carrusel con los cultivos en curso del plan, hectáreas, día del ciclo, etapa y avance | Del Planificador (`GET /api/principal/cultivos-activos`). Cada cultivo del catálogo muestra el **precio** (precio medio rural del último año de SIAP, con una flecha contra su mediana de 10 años), el **rendimiento típico** y chips de rentabilidad, sequía y riesgo hídrico, del estado de la ubicación (o nacionales). SIAP no trae un dato de demanda | **Implementado** |
| **Tareas vencidas**: aviso con las tareas del Planificador sin hacer cuya fecha ya pasó (la más atrasada y cuántas más hay) | `GET /api/principal/tareas-vencidas`; no depende del clima | **Implementado** |
| **Plan anual**: barras por cultivo con fechas y línea de "hoy" | Del Planificador (mismo plan) | **Implementado** |

## 2. Clima

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| **Selector de día** (anterior/siguiente) | Pasado: NASA POWER (diario). Futuro: Open-Meteo | Resuelto |
| **Condiciones locales** del día: temperatura, sensación, humedad, viento, probabilidad y mm de lluvia, humedad del suelo (a 20 cm), temperatura del suelo | POWER (temperatura, lluvia, humedad, humedad de suelo) y Open-Meteo (temperatura del suelo probada a 0 cm; otras profundidades no probadas) | Parcial |
| Mensaje "Condiciones favorables / ventana óptima para labores hasta las 16:30" | Regla nuestra sobre el pronóstico por hora (Open-Meteo o SMN `method=3`) | Parcial |
| **Mapa climático global** con capas Temperatura, Precipitación y Suelo; puntos con ciudades (Monterrey, Madrid, Sídney) | Capas NASA (IMERG para lluvia, SMAP para suelo) o puntos de Open-Meteo por ciudad. No probé servicios de mapas de NASA | Falta investigar |

## 3. Mercado

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| **Rango**: 1 semana, 1 mes, 1 año | Precios diarios: SNIIM (sin API, habría que extraerlo de sus páginas). SIAP solo trae precios **anuales** por municipio | **Falta** para semana y mes; parcial para año |
| **Cultivos seleccionados** (casillas): maíz amarillo, trigo cristalino, frijol pinto | Lista de cultivos del módulo Cultivos | Resuelto |
| Interruptor **gráficas combinadas** | Solo interfaz | Resuelto |
| Gráfica **Fluctuación de precios** (MXN por tonelada) con **Compra, Venta y Predicción** (línea punteada) | Compra/Venta: SNIIM da precios de mayoreo, pero no revisé si distingue compra y venta. Predicción: no hay fuente, sería un modelo o tendencia simple por definir | Falta |
| Tarjeta **Mejor oportunidad** ("el maíz subió 8.4% este mes") | Se calcula con la serie de precios | Depende de la serie |

## 4. Cultivos

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| **Biblioteca** con buscador y favoritos: maíz amarillo, frijol pinto, trigo cristalino, sorgo, aguacate Hass (tipo y ciclo) | Lista nuestra, ligada a SIAP y EcoCrop. SIAP lo vi como "Maíz grano"; no revisé si separa variedades como "amarillo" | Parcial |
| Ficha: nombre científico, tipo (cereal, leguminosa, frutal), **ciclo en días**, **consumo de agua** | EcoCrop (nombre científico y ciclo `GMIN/GMAX`; para maíz da 65–365 días, más amplio que el 120–150 del Figma). Agua: FAO-56 o rango de lluvia de EcoCrop | Resuelto con ajustes |
| Chips **Alta rentabilidad**, **Rotación favorable** (compatible con leguminosas), **Sensible a sequía** | Rentabilidad: precio × rendimiento de SIAP. Rotación: familia de la planta en EcoCrop (heurística). Sequía: rango de lluvia | Parcial |
| **Para tu situación actual**: precio sobre el promedio, riesgo hídrico próximo | Precio de SIAP/SNIIM y pronóstico de lluvia | Parcial |
| **Acerca de este cultivo**: texto, suelo preferido, pH, **siembra ideal** (marzo–junio), **temperatura óptima**, **rendimiento** (t/ha) | Texto: lo escribimos nosotros. pH y temperatura: EcoCrop (para maíz da 18–33 °C y pH 5–7). Rendimiento: SIAP. **Siembra ideal por cultivo: no hay dato descargable** | Parcial |

## 5. Planificador (la "línea de tiempo")

Es el gestor de proyectos de cultivos del documento original. Los datos se guardan en SQLite
(`backend/data/planificador.db`, un solo usuario, varios planes).

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| Planes: crear, renombrar y borrar varios planes; parcelas con hectáreas y ciclo | Lo captura el usuario (SQLite) | **Implementado** |
| **Calendario por parcela**: barras por cultivo con fechas, línea de "hoy", añadir/editar/borrar parcelas y siembras en un popup. Ventana de tiempo libre (zoom de 3 a 36 meses, hasta ±10 años) que se mueve arrastrando, con la rueda, con el teclado o con la barra de tiempo. Las siembras de una parcela que quedan fuera de la ventana se cuentan con chips "← N earlier" y "N later →" que saltan a la más cercana | Lo captura el usuario; la cosecha se propone con el ciclo del cultivo | **Implementado** |
| **Sin traslapes**: no se puede sembrar sobre otra siembra de la misma parcela (el día de cosecha cuenta; la siguiente puede empezar al día siguiente). Los nombres de cultivos no distinguen mayúsculas ni acentos y sugieren "¿Quisiste decir…?" para no duplicar | Reglas del backend | **Implementado** |
| **Popup de cada siembra** con cuatro pestañas: **Overview** (estado, avance del ciclo, parcela, economía, siembra anterior y siguiente), **Tasks**, **Crop guide** (cuándo sembrar, ficha del cultivo, agenda INIFAP y clima de NASA) y **Edit** | Del plan | **Implementado** |
| **Cultivos del catálogo de Cultivos**: al sembrar se elige entre los 399 cultivos del catálogo (nombre, tipo y ciclo salen de ahí; se agregan al Planificador al guardar). Los cultivos de demo se enlazaron al catálogo. En la pestaña Crop guide aparece la **ficha del cultivo**: temperatura ideal, uso de agua, pH, si fija nitrógeno, suelo y cuidados, más una línea que compara el **pH de tu suelo** (módulo Suelo) con el rango ideal del cultivo y otra con la **textura** de tu suelo junto a la que prefiere el cultivo según EcoCrop (sin veredicto: no hay equivalencia oficial entre sus clases y las del USDA; solo ~65 cultivos la traen) | `services/catalogo_cultivos.py` sobre `services/cultivos.py` (`GET /api/planificador/catalogo`, `POST /api/planificador/cultivos/desde-catalogo`, `GET /api/planificador/cultivos/{id}/ficha`). El texto de las fichas es borrador general; las agendas INIFAP por estado (`manejo`) aún no se usan | **Implementado** |
| **Costos e ingresos por siembra** (opcional): rendimiento (t/ha), precio (MXN/t) y costo (MXN/ha). Calcula ingreso, costo y ganancia estimados de cada siembra y la suma del plan en el resumen. Al capturarlos ofrece cifras de partida: las tablas de costos del INIFAP del estado (temporal o riego) y la mediana nacional de SIAP | `siembra.rendimiento_t_ha / precio_t / costo_ha` (migración 5); cifras de partida en `GET /api/planificador/catalogo/{id}/ficha`. Cada cifra solo sale si hay datos para calcularla; son estimaciones, no un pronóstico | **Implementado** |
| **Tareas por siembra**: fertilizar, regar, deshierbe, plagas, cosecha u otras, con fecha y marca de hecha; las vencidas se marcan y el resumen del plan cuenta las abiertas y las vencidas. Puede crear un calendario sugerido (plantilla general repartida en el ciclo) | Tabla `tarea` (se borra con la siembra), `services/tareas.py` y `/api/planificador/siembras/{id}/tareas` | **Implementado** |
| **Copiar y exportar el plan**: *Copy to another year* crea un plan nuevo con las mismas parcelas y siembras (con su economía) moviendo las fechas 0 a 3 años; *Export CSV* baja el plan para Excel o Google Sheets y *Export PDF* lo baja con su resumen, un calendario por parcela y la economía | `services/plan_extras.py`: `POST /planes/{id}/duplicar` y `GET /planes/{id}/exportar`; `services/plan_pdf.py`: `GET /planes/{id}/exportar-pdf` (librería `fpdf2`, texto Latin-1). El CSV protege los nombres que empiezan con = + - @ | **Implementado** |
| **Agenda técnica del INIFAP por estado** en la pestaña Crop guide: siembra, variedades, densidad, fertilización, riego, malezas, plagas, enfermedades, cosecha y cuidados. Cada ubicación guarda su estado: las 4 de inicio y los lugares que se buscan por nombre ya lo traen; en "My location" se elige una vez | Agendas INIFAP 2026 (`backend/data/inifap/cuidados`) vía `services/cultivos.manejo`; estado en `ubicacion.cve_ent` (`GET /api/ubicaciones/estados`, `PATCH /api/ubicaciones/{id}`). El texto es del INIFAP en español (resumido automáticamente) | **Implementado** |
| **Cuándo sembrar aquí**: franja de 12 meses (bueno, regular, malo) y los mejores meses para el cultivo en la ubicación activa; avisa si el mes elegido no conviene o si la lluvia del ciclo no alcanza (hay que regar), y, si la siembra es de aquí a un mes, si el suelo está más seco de lo normal ahora (módulo Suelo, SMAP). Sale en el formulario de siembra y en la pestaña Crop guide; no aplica a cultivos perennes | `services/ventana_siembra.py` (`GET /api/planificador/catalogo/{id}/ventana-siembra`): rango de temperatura ideal y tolerable del catálogo (EcoCrop) contra el clima promedio mensual de NASA POWER (`climatologia`). Puntaje gradual por mes; es una guía por promedios, sin variedades regionales ni heladas puntuales | **Implementado** |
| **Clima observado de NASA POWER** dentro de la pestaña Crop guide: lluvia (mm y días con lluvia), temperatura media, mínima y máxima, humedad de la raíz y radiación solar, desde la siembra (o los últimos 30 días si aún no empieza) en la ubicación activa | NASA POWER (`GET /api/principal/clima-nasa`, caché de 6 h; los datos llevan ~2 días de retraso). Falta la "mejor fecha de siembra" por cultivo, que necesita rangos por cultivo del catálogo | **Implementado** (sin fecha ideal) |
| **Recomendación de rotación**: después de una leguminosa (fija nitrógeno) un cereal; después de un cereal, hortaliza, oleaginosa o tubérculo, una leguminosa. No repite la **familia botánica** del último cultivo y sugiere cualquier cultivo anual del catálogo (prefiere el menos usado en la parcela y, si empatan, el de mayor superficie en México). Sin "% de afinidad" inventado | `services/rotacion.py` con la familia y la fijación de nitrógeno del catálogo (solo los ~80 cultivos curados las traen; en los demás se usa el tipo). Si el último cultivo no es del catálogo, se usa la regla simple por tipo | **Implementado** (sin precio ni agua) |
| **Resumen del plan**: número de siembras, cultivos distintos, próxima cosecha, uso del suelo | Calculado del plan | **Implementado**; la rentabilidad depende de SIAP |

## 6. Noticias

Mezcla **avisos propios** (calculados con los datos del usuario, siempre disponibles) y **titulares
externos** de feeds RSS en inglés. Si un feed falla, se omite y la pantalla avisa sin romperse.

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| Filtros All / My farm / Weather / Research | Solo interfaz | **Implementado** |
| **Avisos propios**: alertas de clima y plagas, tareas vencidas, cosechas que llegan en 45 días o menos, y la lluvia de los últimos 30 días en la ubicación activa. Cada uno abre la pantalla relacionada | Alertas (`services/alertas.py`), plan del Planificador y NASA POWER (`services/noticias.py`, `GET /api/noticias`) | **Implementado** |
| **Titulares externos** con enlace a la fuente original | Feeds RSS de CIMMYT (centro internacional de maíz y trigo) y NASA Earth Observatory, con caché de 30 min. FAO, USDA y SADER no tienen feed utilizable (probados el 2026-11-14) | **Implementado** |
| Precio del maíz y programas de agua del Figma | Dependen de Mercado y de una fuente de programas que no existe | Falta |

## 7. Suelo

Pantalla propia (en el Figma original no existía). Dice cómo está el suelo hoy y hacia dónde va, con
escalas de colores de reglas oficiales y una ayuda en pantalla para los términos técnicos. Todo sale del
punto de cultivo más cercano a la ubicación activa (NASA MODIS). Detalle de fuentes, reglas y endpoints en
[suelo.md](suelo.md).

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| **Water in your soil**: humedad de hoy contra otros años en esta época | SMAP, percentil con las categorías del Monitor de Sequía (`/api/suelo/estado`) | **Implementado** |
| **Plants on your land**: cuántas plantas cubren el terreno y el mes con menos | MODIS NDVI, escala USGS (`/api/suelo/cobertura`) | **Implementado** |
| **Shape of the land**: pendiente y qué tanto favorece perder suelo con la lluvia | SRTM, clase FAO y factor LS de RUSLE (`/api/suelo/erosion`) | **Implementado** |
| **Underground water**: tendencia de la región desde 2002 | GRACE / GRACE-FO (`/api/suelo/agua-subterranea`) | **Implementado** |
| **Soil type**: textura, pH y materia orgánica | SoilGrids, triángulo USDA (`/api/suelo/propiedades`) | **Implementado** |
| Detalles técnicos: humedad y temperatura por capa, evaporación, tendencia histórica, retención | NASA POWER y SMAP (`/actual`, `/historico`, `/raiz`, `/retencion`, `/smap`) | **Implementado** |
| El pH y la humedad también salen en **Principal**, en el popup del cultivo y en las alertas | `services/suelo_ubicacion.py`: misma cifra que esta pantalla | **Implementado** |

## Qué cambió respecto al documento original

| Documento original | Figma |
|---|---|
| Ubicación (pantalla aparte) | Ya no es pantalla: es el selector de municipio de arriba |
| Suelo (pantalla aparte, "similar al clima") | Sigue siendo pantalla (**Soil**, sección 7); además su pH y humedad salen en Principal |
| Línea de tiempo | Se llama **Planificador** |
| — | **Noticias** es nueva |
| Datos de México | El mapa de Clima es global (Monterrey, Madrid, Sídney) |

## Qué datos del Figma todavía no tienen fuente

1. Precios de mercado diarios (semana/mes) y la distinción compra/venta.
2. Predicción de precios.
3. Alertas oficiales (huracán, lluvia intensa) y pronóstico a un mes. (Las alertas de clima y plagas
   de Principal ya se calculan con nuestras reglas; esto se refiere a avisos oficiales.)
4. ~~Contenido de Noticias~~ (resuelto: avisos propios y feeds de CIMMYT y NASA; falta lo de precios).
5. Siembra ideal por cultivo.
6. Capas del mapa global.

## Preguntas para decidir

1. ~~¿Dónde se guardan las parcelas y planes del usuario?~~ Resuelto: SQLite en `backend/data/` (un solo usuario por ahora).
2. **¿Mercado con datos reales o con serie anual de SIAP?** Con SIAP solo hay vista de 1 año; semana y mes exigen el scraper de SNIIM.
3. ~~¿Noticias reales, escritas por nosotros o calculadas?~~ Resuelto: calculadas con nuestros datos más feeds externos.
4. **¿El mapa global usa capas NASA o puntos por ciudad?**
5. ~~¿Qué ciudades?~~ Resuelto: 4 de inicio más las que agregue el usuario (solo México). Falta ligar cada lugar con SIAP.
6. ~~Estructura de carpetas~~: ya está ajustada al Figma (`pages/` tiene Principal, Clima, Mercado, Cultivos, Planificador y Noticias).
