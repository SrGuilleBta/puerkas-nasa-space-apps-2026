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
- Falta una noticia de **precios** (depende de Mercado) y más fuentes si aparece algún feed de
  México o la FAO que responda.
- La **alerta regional** de Principal sigue con texto de ejemplo y enlaza a Noticias: conectarla
  con una noticia real (por ejemplo, la alerta más grave).

## Alertas de Principal

- **Plagas y enfermedades:** el equipo pondrá la información después. Hoy son reglas generales en
  `backend/app/services/alertas.py` (hongos, pulgón y mosca blanca, gusano cogollero en maíz). Cambiar
  textos, cultivos y umbrales cuando llegue esa información.
- El pronóstico llega hasta el domingo, así que las alertas del domingo ven solo ese día.
  Si Clima ofrece más días, usarlos.

## Depende de Cultivos (otro compañero)

- **Catálogo en inglés.** Los nombres de cultivos de hoy (Maíz amarillo, Frijol pinto...) son de demo
  en español; el catálogo de Cultivos vendrá en inglés. Al conectarlo, revisar que los **tipos**
  (`cereal`, `leguminosa`, `frutal`, `hortaliza`, `oleaginosa`, `forraje`, `otro`) sigan siendo los
  mismos valores, porque las reglas de rotación y de plagas dependen de ellos; si llegan en inglés
  hay que hacer un mapa en el backend. La alerta del cogollero ya reconoce "corn" y "maize".

- **Mejor fecha de siembra** por cultivo con el clima histórico de NASA POWER: necesita el rango de
  temperatura y de lluvia de cada cultivo.
- Umbrales de las alertas por cultivo (helada, calor, lluvia).
- Precio, variación y chips de demanda en "Cultivos activos" (SIAP).
- Recomendación de rotación más fina (nitrógeno, agua, raíz, precio) en vez de solo tipo de cultivo.
- Rentabilidad en el resumen del plan.

## Planificador

- Costos e ingresos estimados por siembra (hectáreas, rendimiento y precio editables).
- Tareas por siembra (fertilizar, riego, cosecha) con marca de hecho.
- Copiar el plan de otro año o exportarlo a PDF.
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
