# Pendientes de Principal, Planificador y Noticias

Lista de lo que queda por hacer en las pantallas de Guillermo (actualizada el 2026-11-15).
Lo que ya funciona está en [funcionalidades.md](funcionalidades.md).

## Decidir

- ~~Idioma de la plataforma~~: resuelto. La interfaz (pantallas, fechas y mensajes del backend) está
  en inglés; el código, los comentarios, los docs y los datos (cultivos, planes, parcelas) siguen en
  español. Los tipos de cultivo se guardan en español y se muestran con `utils/tipos.js`.
  Las pantallas nuevas se hacen directamente en inglés.

## Noticias

- Hecha: avisos propios más feeds de CIMMYT y NASA Earth Observatory (en inglés).
- Falta una noticia de **precios** (pendiente extra; depende de Mercado) y más fuentes si aparece
  algún feed de México o la FAO que responda.
- La tarjeta de Principal (antes "alerta regional") ya muestra el último titular de Noticias. Si se
  consigue una fuente oficial de alertas (Protección Civil, SMN), se puede volver a usar ahí.

## Alertas de Principal

- **Plagas y enfermedades:** el equipo pondrá la información después. Hoy son reglas generales en
  `backend/app/services/alertas.py` (hongos, pulgón y mosca blanca, gusano cogollero en maíz). Cambiar
  textos, cultivos y umbrales cuando llegue esa información.
- El pronóstico de Principal cubre hoy y los 6 días siguientes, así que las alertas siempre ven la
  semana que viene. Si Clima ofrece más días, usarlos.

## Catálogo de Cultivos (ya llegó)

- Hecho: el Planificador elige cultivos del catálogo (399) y muestra su ficha en el popup. Migración
  v4: `cultivo.catalogo_id`; los cultivos de demo se renombraron al nombre del catálogo.
- Los **tipos** del catálogo ("Cereal", "Tubérculo", "Industrial"...) se guardan en minúsculas y sin
  acentos; "Semilla" y los que no traen tipo pasan a `otro`. La rotación solo tiene regla para
  cereal y leguminosa.
- Los nombres del catálogo están en español. La traducción está en camino (rama `cultivos_v2`): los
  nombres de los cultivos del Planificador se sincronizan solos con el catálogo al arrancar, y los tipos
  se aceptan en español o inglés ("Leguminosa" o "Legume"). Al fusionarla, revisar que sigan igual los
  ids del catálogo y los campos `ciclo_dias`, `temperatura_*` y `fija_nitrogeno`.
- Las agendas INIFAP ya se usan (estado guardado en cada ubicación). Falta usar los **meses de siembra** de
  esas agendas para afinar la franja de "cuándo sembrar aquí".

## Lo que sigue

- ~~Conectar Suelo~~: hecho en Principal (pH y humedad del módulo Suelo), el popup del cultivo (pH del suelo contra el ideal) y las alertas (suelo más seco de lo normal, SMAP). También hecho: la franja de "cuándo sembrar aquí" avisa si el suelo está más seco de lo normal y la ficha muestra la textura del suelo junto a la que prefiere el cultivo (EcoCrop; solo ~65 de 399 cultivos la traen, y sin veredicto porque no hay equivalencia oficial entre las clases de EcoCrop y las del USDA). El `services/soilgrids.py` viejo ya se borró.

- ~~Mejor fecha de siembra~~: hecha con temperatura (catálogo contra NASA POWER). Mejoras: usar los meses
  de siembra de las agendas INIFAP cuando haya estado, sumar el pH y el suelo cuando esté esa parte, y
  afinar con variedades (el trigo de otoño sale "regular" porque EcoCrop trae un solo rango de temperatura).
- ~~Umbrales de las alertas por cultivo~~: hecho para helada y calor (rango absoluto de temperatura del
  catálogo). También hecha la lluvia por cultivo (déficit y encharcamiento; solo ~78 de 399 cultivos traen su rango
  de lluvia). Falta las plagas por cultivo con el motor de la rama `plagas`.
- ~~Precio, rendimiento y chips en "Cultivos activos"~~: hecho con SIAP (estado de la ubicación o, si no, nacional). Un dato de **demanda** no existe en SIAP: se muestra la variación del precio contra su mediana de 10 años. Falta: la demanda real, si aparece una fuente (Mercado).
- ~~Rotación más fina~~: hecha con familia y nitrógeno. Mejoras: usar el precio y el agua; sólo ~80 de 399
  cultivos traen familia y marca de nitrógeno (los demás se deducen del tipo).
- Rentabilidad en el resumen del plan.

## Planificador

- Hechos: costos e ingresos por siembra, tareas por siembra, copiar el plan a otro año, exportar a CSV
  y la agenda del INIFAP por estado.
- ~~Exportar a PDF~~: hecho (resumen, calendario por parcela y tabla de siembras con su economía). Usa la librería
  `fpdf2`: tras bajar este cambio hay que recrear el backend (`docker compose up -d --force-recreate backend`).
  Solo cubre texto en Latin-1 (acentos y ñ sí; otros alfabetos salen como "?").
- ~~Tareas vencidas en Principal y Noticias~~: hecho (aviso ámbar en Principal y noticia propia). Las tareas
  no se copian al duplicar el plan a propósito: son del ciclo que ya pasó.
- El calendario sugerido de tareas es una plantilla general; se podría armar con las etapas del cultivo y
  los cuidados de la agenda del INIFAP.
- El texto del INIFAP está en español (la rama `cultivos_v2` lo traduce); la mediana nacional como cifra de
  partida no es precio de mercado de hoy.
- ~~Indicadores "N earlier / N later" de siembras fuera de la vista en el calendario~~: hechos (y saltan a la más cercana).

## Por verificar

- Gestos táctiles en un celular real (calendario y barra de tiempo).
- La detección automática de ubicación la primera vez que se abre la app.
- Con Windows sin servicios de ubicación el botón "Usar mi ubicación" falla; el respaldo es agregar
  el lugar por nombre.
- El popup de siembra puede quedar con scroll en pantallas bajas (aceptado).

## Pequeños

- ~~Datos de ejemplo (`datosEjemplo.js`)~~: borrados; ya nada los usaba.
- ~~"Mi parcela" del menú lateral~~: ahora muestra el plan activo (nombre, parcelas y hectáreas).
- Las columnas `lat_suelo` y `lon_suelo` de la tabla `ubicacion` ya no se leen (Suelo usa el punto de MODIS).
  Se pueden quitar con una migración de la base.
