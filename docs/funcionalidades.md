# Qué hará cada parte del sistema (v1, borrador)

Basado en el prototipo de Figma ("CroPro", [enlace en el README](../README.md)). Lo leí recorriendo
las pantallas de la vista previa el 2026-11-14; no tengo acceso al código del Figma. **Los números,
fechas y nombres del Figma son ejemplos** (todo aparece en junio de 2025 con datos inventados): lo
que importa es qué muestra cada pieza, no el valor.

Para cada pantalla: qué muestra, de dónde saldría cada dato (fuentes en [datos.md](datos.md)) y si
el dato está **resuelto**, **parcial** o **falta**. Es un punto de partida para mejorarlo.

## Piezas compartidas (en todas las pantallas)

| Pieza | Qué hace | Dato / fuente | Estado |
|---|---|---|---|
| Selector de **municipio** (arriba) | Elige dónde estás: Monterrey NL, Saltillo COAH, Culiacán SIN, Mérida YUC. Todo lo demás se recalcula para ese lugar | Geocodificación de Open-Meteo para lat/lon; hay que ligar cada ciudad con el estado/municipio de SIAP | Resuelto (geocoding probado); la equivalencia con SIAP hay que armarla |
| "Datos actualizados 09:42" | Hora de la última consulta | La marca el backend al responder | Resuelto |
| Menú lateral | Principal, Clima, Mercado, Cultivos, Planificador, Noticias | Solo navegación | Resuelto |
| "Mi parcela" (abajo del menú) | Muestra la parcela del usuario (ej. "La Esperanza", 12.4 ha) | Datos que captura el usuario | Falta decidir dónde se guardan (ver "Preguntas") |

## 1. Principal

Resumen de todo en una pantalla.

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| **Banner "Atención preventiva"** (ej. "frente de lluvia intensa el próximo mes") | Pronóstico a un mes: no hay fuente | Falta |
| **Pronóstico semanal**: 7 días con temperatura y % de lluvia, marcando "hoy", badge "DATOS REALES" | Open-Meteo (7 días, Tmax/Tmin, lluvia). El % de lluvia no lo probé; el SMN da probabilidad pero solo 4 días | Parcial |
| **Condiciones de hoy**: temperatura, sensación térmica, cielo, "óptimo para campo", humedad, viento, humedad del suelo, pH del suelo | Humedad del suelo: Open-Meteo / NASA POWER. pH: SoilGrids. Sensación, humedad y viento: Open-Meteo (no probados) y SMN (viento y nubosidad probados). "Óptimo para campo" es una regla nuestra | Parcial |
| **Alerta regional** (ej. huracán, "hace 35 min", Protección Civil) | Alertas oficiales: no verifiqué ninguna API | Falta |
| **Cultivos activos**: cultivo en curso, hectáreas, día del ciclo, "etapa 3 de 5", precio actual y variación, cosecha estimada, chips "Alta demanda" y "Estrés hídrico" | Del plan del usuario + SIAP (precio, rendimiento) + EcoCrop (ciclo en días). La etapa y la cosecha estimada se calculan con la fecha de siembra y el ciclo | Parcial |
| **Plan anual**: barras por cultivo con fechas, línea de "hoy", filtro por estación | Del Planificador (misma información) | Depende del Planificador |

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

Es el gestor de proyectos de cultivos del documento original.

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| Plan principal: parcelas, hectáreas y ciclo, con botón **Nuevo plan** y zoom | Lo captura el usuario | Falta dónde guardarlo |
| **Calendario por parcela** (ene–dic): barras por cultivo con fechas, línea de "hoy", **Añadir parcela**, **Editar** cultivo | Lo captura el usuario; las barras usan fechas y ciclo | Falta dónde guardarlo |
| **Recomendación inteligente**: "después del maíz, considera… frijol 92% de afinidad (restaura nitrógeno, bajo consumo de agua)" | Puntaje de rotación. Es el centro del reto de NASA: hay que armar la tabla de rasgos (nitrógeno, agua, raíz, precio, clima) con EcoCrop + FAO-56 + SIAP | Parcial |
| **Resumen del ciclo**: número de cultivos, % de uso del suelo, % de rentabilidad | Calculado del plan y de SIAP | Parcial |

## 6. Noticias

| Qué muestra | Dato / fuente | Estado |
|---|---|---|
| Filtros Todas / Clima / Mercado / Región | Solo interfaz | Resuelto |
| Tarjetas: alerta regional, precio del maíz, programas de agua, cultivos alternativos | No hay fuente definida (no verifiqué ninguna): podría ser contenido que escribimos, alertas calculadas con nuestros datos, o un feed externo | **Falta decidir** |

## Qué cambió respecto al documento original

| Documento original | Figma |
|---|---|
| Ubicación (pantalla aparte) | Ya no es pantalla: es el selector de municipio de arriba |
| Suelo (pantalla aparte, "similar al clima") | Ya no es pantalla: son tarjetas en Principal y Clima y una capa del mapa |
| Línea de tiempo | Se llama **Planificador** |
| — | **Noticias** es nueva |
| Datos de México | El mapa de Clima es global (Monterrey, Madrid, Sídney) |

## Qué datos del Figma todavía no tienen fuente

1. Precios de mercado diarios (semana/mes) y la distinción compra/venta.
2. Predicción de precios.
3. Alertas oficiales (huracán, lluvia intensa) y pronóstico a un mes.
4. Contenido de Noticias.
5. Siembra ideal por cultivo.
6. Capas del mapa global.

## Preguntas para decidir

1. **¿Dónde se guardan las parcelas y planes del usuario?** El backend hoy no guarda nada. Opciones: un archivo SQLite en el backend (se comparte entre usuarios) o `localStorage` del navegador (solo guarda en el equipo de cada usuario).
2. **¿Mercado con datos reales o con serie anual de SIAP?** Con SIAP solo hay vista de 1 año; semana y mes exigen el scraper de SNIIM.
3. **¿Noticias reales, escritas por nosotros o calculadas?**
4. **¿El mapa global usa capas NASA o puntos por ciudad?**
5. **¿Qué ciudades?** El Figma trae 4; hay que ligar cada una con SIAP.
6. ~~Estructura de carpetas~~: ya está ajustada al Figma (`pages/` tiene Principal, Clima, Mercado, Cultivos, Planificador y Noticias).
