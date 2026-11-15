# Pendientes de Principal, Planificador y Noticias

Lista de lo que queda por hacer en las pantallas de Guillermo (actualizada el 2026-11-14).
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
- El pronóstico llega hasta el domingo, así que las alertas del domingo ven solo ese día.
  Si Clima ofrece más días, usarlos.

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

- ~~Conectar Suelo~~: hecho en Principal (pH y humedad del módulo Suelo), el popup del cultivo (pH del suelo contra el ideal) y las alertas (suelo más seco de lo normal, SMAP). Falta usar el suelo en la franja de "cuándo sembrar aquí" y la textura en las fichas. `services/soilgrids.py` (viejo) ya no se usa: se puede borrar.

- ~~Mejor fecha de siembra~~: hecha con temperatura (catálogo contra NASA POWER). Mejoras: usar los meses
  de siembra de las agendas INIFAP cuando haya estado, sumar el pH y el suelo cuando esté esa parte, y
  afinar con variedades (el trigo de otoño sale "regular" porque EcoCrop trae un solo rango de temperatura).
- ~~Umbrales de las alertas por cultivo~~: hecho para helada y calor (rango absoluto de temperatura del
  catálogo). También hecha la lluvia por cultivo (déficit y encharcamiento; solo ~78 de 399 cultivos traen su rango
  de lluvia). Falta las plagas por cultivo con el motor de la rama `plagas`.
- Precio, rendimiento y chips de demanda en "Cultivos activos" (SIAP, vía el catálogo).
- ~~Rotación más fina~~: hecha con familia y nitrógeno. Mejoras: usar el precio y el agua; sólo ~80 de 399
  cultivos traen familia y marca de nitrógeno (los demás se deducen del tipo).
- Rentabilidad en el resumen del plan.

## Planificador

- Hechos: costos e ingresos por siembra, tareas por siembra, copiar el plan a otro año, exportar a CSV
  y la agenda del INIFAP por estado.
- Exportar a PDF (hoy solo CSV).
- Las tareas no se copian al duplicar el plan y no aparecen todavía en Principal ni en Noticias (por ejemplo
  "tienes 3 tareas vencidas").
- El calendario sugerido de tareas es una plantilla general; se podría armar con las etapas del cultivo y
  los cuidados de la agenda del INIFAP.
- El texto del INIFAP está en español (la rama `cultivos_v2` lo traduce); la mediana nacional como cifra de
  partida no es precio de mercado de hoy.
- Indicadores por fila de siembras fuera de la vista ("N antes / N después") en el calendario.

## Por verificar

- Gestos táctiles en un celular real (calendario y barra de tiempo).
- La detección automática de ubicación la primera vez que se abre la app.
- Con Windows sin servicios de ubicación el botón "Usar mi ubicación" falla; el respaldo es agregar
  el lugar por nombre.
- El popup de siembra puede quedar con scroll en pantallas bajas (aceptado).

## Pequeños

- Los datos de ejemplo de `frontend/src/api/datosEjemplo.js` (alerta regional y parcela del menú)
  se borran cuando dejen de usarse.
- La parcela "Mi parcela" del menú lateral sigue siendo un ejemplo fijo.
