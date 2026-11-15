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
- Los nombres del catálogo están en español. Cuando Cultivos los pase a inglés, no hay que tocar nada
  salvo la migración de nombres de demo si cambian.
- **Falta usar:** las agendas INIFAP por estado (`manejo` en `services/cultivos.py`) y la ventana de
  siembra por mes. Necesitan saber el estado de la ubicación (hoy solo guardamos lat/lon).

## Lo que sigue

- **Mejor fecha de siembra** por cultivo: rango de temperatura del catálogo contra el clima histórico
  de NASA POWER (y los meses de siembra de las agendas INIFAP cuando haya estado).
- Umbrales de las alertas por cultivo (helada, calor, lluvia) con los rangos de EcoCrop del catálogo.
- Precio, rendimiento y chips de demanda en "Cultivos activos" (SIAP, vía el catálogo).
- Recomendación de rotación más fina con familia y fijación de nitrógeno del catálogo.
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
