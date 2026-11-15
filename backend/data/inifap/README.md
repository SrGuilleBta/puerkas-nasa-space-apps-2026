# INIFAP — Agendas Técnicas Agrícolas 2026

Fuente de los textos de manejo por estado (`cuidados/<estado>.json`) que usa
`/api/cultivos/viabilidad`. Hay una agenda por estado, edición 2026, con la misma plantilla en
todos. **Ciudad de México no tiene agenda (nunca se ha publicado una); la API usa la del Estado
de México.**

Los PDF y el texto extraído **no se versionan** (`agendas/` y `extraido/` están en `.gitignore`).
Solo se versiona `cuidados/`.

| Carpeta | Contenido | ¿En git? |
|---|---|---|
| `agendas/` | PDF originales, renombrados como `<estado>.pdf` | No |
| `extraido/` | Texto por cultivo y sección, más los cuadros de costos (salida de `python -m pipeline.inifap`) | No |
| `cuidados/` | Resumen curado por estado: siembra, manejo, plagas, cuidados | Sí |

## Cómo actualizar

1. Descargar los PDF **desde el navegador** en la biblioteca del INIFAP (vun.inifap.gob.mx). El
   sitio tiene un firewall anti-bots que bloquea las descargas automáticas.
2. Guardarlos en `agendas/` con el nombre de la tabla. Si se bajan con su nombre original, el
   renombrado es: quitar el prefijo numérico y `Agenda_Técnica_Agrícola_2026_`, pasar a
   minúsculas y sin acentos, y `estado_de_mexico` → `mexico`.
3. Desde `backend/`: `python -m pipeline.inifap`. Revisar los avisos de cada
   `extraido/<estado>.json` (fichas sin secciones o sin costos, encabezados no reconocidos).
4. Resumir `extraido/<estado>.json` en `cuidados/<estado>.json` siguiendo
   [instrucciones_resumen.md](../../pipeline/inifap/instrucciones_resumen.md) (con Claude, usando
   solo el texto de la agenda). Ver [docs/cultivos-pipeline.md](../../../docs/cultivos-pipeline.md).

## Archivos (edición 2026)

| Estado | Nombre original del PDF | Guardar como |
|---|---|---|
| Aguascalientes | `14834_5698_Agenda_Técnica_Agrícola_2026_Aguascalientes.pdf` | `aguascalientes.pdf` |
| Baja California | `14835_5699_Agenda_Técnica_Agrícola_2026_Baja_California.pdf` | `baja_california.pdf` |
| Baja California Sur | `14836_5700_Agenda_Técnica_Agrícola_2026_Baja_California_Sur.pdf` | `baja_california_sur.pdf` |
| Campeche | `14837_5701_Agenda_Técnica_Agrícola_2026_Campeche.pdf` | `campeche.pdf` |
| Chiapas | `14838_5702_Agenda_Técnica_Agrícola_2026_Chiapas.pdf` | `chiapas.pdf` |
| Chihuahua | `14839_5703_Agenda_Técnica_Agrícola_2026_Chihuahua.pdf` | `chihuahua.pdf` |
| Coahuila | `14840_5704_Agenda_Técnica_Agrícola_2026_Coahuila.pdf` | `coahuila.pdf` |
| Colima | `14841_5705_Agenda_Técnica_Agrícola_2026_Colima.pdf` | `colima.pdf` |
| Durango | `14842_5706_Agenda_Técnica_Agrícola_2026_Durango.pdf` | `durango.pdf` |
| Estado de México | `14843_5707_Agenda_Técnica_Agrícola_2026_Estado_de_México.pdf` | `mexico.pdf` |
| Guanajuato | `14844_5708_Agenda_Técnica_Agrícola_2026_Guanajuato.pdf` | `guanajuato.pdf` |
| Guerrero | `14845_5709_Agenda_Técnica_Agrícola_2026_Guerrero.pdf` | `guerrero.pdf` |
| Hidalgo | `14846_5710_Agenda_Técnica_Agrícola_2026_Hidalgo.pdf` | `hidalgo.pdf` |
| Jalisco | `14847_5711_Agenda_Técnica_Agrícola_2026_Jalisco.pdf` | `jalisco.pdf` |
| Michoacán | `14848_5712_Agenda_Técnica_Agrícola_2026_Michoacán.pdf` | `michoacan.pdf` |
| Morelos | `14849_5713_Agenda_Técnica_Agrícola_2026_Morelos.pdf` | `morelos.pdf` |
| Nayarit | `14850_5714_Agenda_Técnica_Agrícola_2026_Nayarit.pdf` | `nayarit.pdf` |
| Nuevo León | `14851_5715_Agenda_Técnica_Agrícola_2026_Nuevo_León.pdf` | `nuevo_leon.pdf` |
| Oaxaca | `14852_5716_Agenda_Técnica_Agrícola_2026_Oaxaca.pdf` | `oaxaca.pdf` |
| Puebla | `14853_5717_Agenda_Técnica_Agrícola_2026_Puebla.pdf` | `puebla.pdf` |
| Querétaro | `14854_5718_Agenda_Técnica_Agrícola_2026_Querétaro.pdf` | `queretaro.pdf` |
| Quintana Roo | `14855_5719_Agenda_Técnica_Agrícola_2026_Quintana_Roo.pdf` | `quintana_roo.pdf` |
| San Luis Potosí | `14856_5720_Agenda_Técnica_Agrícola_2026_San_Luis_Potosí.pdf` | `san_luis_potosi.pdf` |
| Sinaloa | `14857_5721_Agenda_Técnica_Agrícola_2026_Sinaloa.pdf` | `sinaloa.pdf` |
| Sonora | `14858_5722_Agenda_Técnica_Agrícola_2026_Sonora.pdf` | `sonora.pdf` |
| Tabasco | `14859_5723_Agenda_Técnica_Agrícola_2026_Tabasco.pdf` | `tabasco.pdf` |
| Tamaulipas | `14860_5724_Agenda_Técnica_Agrícola_2026_Tamaulipas.pdf` | `tamaulipas.pdf` |
| Tlaxcala | `14865_5725_Agenda_Técnica_Agrícola_2026_Tlaxcala.pdf` | `tlaxcala.pdf` |
| Veracruz | `14862_5726_Agenda_Técnica_Agrícola_2026_Veracruz.pdf` | `veracruz.pdf` |
| Yucatán | `14863_5727_Agenda_Técnica_Agrícola_2026_Yucatán.pdf` | `yucatan.pdf` |
| Zacatecas | `14864_5728_Agenda_Técnica_Agrícola_2026_Zacatecas.pdf` | `zacatecas.pdf` |

## Notas de la extracción (corrida del 2026-11-14)

- 297 fichas extraídas en 31 estados (298 resumidas: la Chía de Guanajuato se separó a mano).
- **Michoacán** viene sin saltos de línea: sus 12 fichas se guardan como `texto_completo`, sin
  separar en secciones.
- En muchas fichas la siembra, el riego y la fertilización no tienen encabezado propio y quedan
  dentro de la sección `manejo`.
