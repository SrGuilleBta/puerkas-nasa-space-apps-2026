# Instrucciones para resumir una Agenda Técnica INIFAP 2026

Estas instrucciones son para quien convierta `backend/data/inifap/extraido/<estado>.json` (texto
extraído por `python -m pipeline.inifap`) en `backend/data/inifap/cuidados/<estado>.json` (lo que
lee la API). Se escribieron para que lo haga Claude, pero valen para una persona.

## Reglas de contenido (obligatorias)

1. **Usar solo el texto de la agenda.** Nada de conocimiento propio. Si un dato no está en el
   texto, el campo va en `null` (o `[]` en listas). Es mejor un campo vacío que uno inventado.
2. **Nada de marcas comerciales ni dosis de plaguicidas** (insecticidas, fungicidas, herbicidas).
   Se nombran las plagas, enfermedades y malezas, y las prácticas de manejo (umbral, momento,
   control cultural o biológico), pero no el producto ni la dosis: algunos pueden estar
   prohibidos. Las dosis de **fertilizante** sí van (fórmulas N-P-K, kg/ha).
3. **Los valores se escriben en inglés** (las llaves del JSON se quedan en español). Frases cortas,
   sin copiar párrafos enteros. Usa la terminología de
   [glosario_en.json](../cultivos/glosario_en.json) y los valores fijos de
   [instrucciones_traduccion.md](../cultivos/instrucciones_traduccion.md) (`modalidad`: `irrigated`/`rainfed`,
   `tipo_cultivo`: `annual`/`perennial`, `fuente` con el título original y su traducción entre corchetes).
4. **Páginas:** usar `paginas` de la ficha extraída tal cual.
5. Todas las fichas llevan `"revisado": false`.

## Cómo leer el extraído

Cada ficha en `extraido/<estado>.json` tiene: `ficha`, `cientifico`, `tipo_cultivo`,
`regimen_hidrico`, `paginas`, `secciones` (dict sección → texto) y `costos` (cuadros ya parseados).
Secciones posibles: `introduccion`, `region`, `manejo`, `terreno`, `siembra`, `fecha_siembra`,
`densidad`, `riego`, `fertilizacion`, `plagas`, `enfermedades`, `malezas`, `variedades`, `labores`,
`cosecha`, o un solo `texto_completo` cuando el PDF no se pudo separar (Michoacán).

- La fecha de siembra suele estar en `siembra` o en `manejo` (busca "fecha", "época", meses).
- Las tablas de plaguicidas salen como texto revuelto: úsalas solo para saber qué plagas hay.
- Los textos son largos: léelos por ficha con Python y no los imprimas completos de una vez. En
  Windows, usa `python -I` y `sys.stdout.reconfigure(encoding="utf-8")` antes de imprimir.

## Ids de cultivo (`cultivo_ids`)

Cada ficha debe apuntar a uno o más ids de `backend/data/cultivos/catalogo.json` (ids de SIAP).
Solo se aceptan ids que existan en ese catálogo; compruébalo con Python. Ejemplos: Maíz grano →
`maiz-grano`; Maíz forrajero → `maiz-forrajero-en-verde`; Frijol → `frijol`; Garbanzo →
`garbanzo-grano`; Soya → `soya`; Soya para semilla → `semilla-de-soya`; Trigo → `trigo-grano`;
Sorgo grano → `sorgo-grano`; Sorgo forrajero → `sorgo-forrajero-en-verde`; Alfalfa →
`alfalfa-verde`; Jitomate o tomate rojo → `tomate-rojo-jitomate`; Limón persa o mexicano →
`limon`; Mijo perla → `mijo`. Si no hay id razonable, deja `[]` y explícalo en `nota`.

## Formato de salida: `cuidados/<estado>.json`

```json
{
  "_nota": "Resumen de la Agenda Técnica Agrícola 2026 del INIFAP, hecho a partir del texto de data/inifap/extraido/<estado>.json siguiendo pipeline/inifap/instrucciones_resumen.md. Sin marcas ni dosis de plaguicidas.",
  "cve_ent": "25",
  "estado": "Sinaloa",
  "edicion": 2026,
  "fuente": "INIFAP. Agenda Técnica Agrícola de Sinaloa. INIFAP, Ciudad de México, 2026.",
  "fichas": [
    {
      "ficha": "Frijol",
      "cientifico": "Phaseolus vulgaris L.",
      "paginas": [31, 40],
      "cultivo_ids": ["frijol"],
      "tipo_cultivo": "anual",
      "modalidad": "riego",
      "ciclo": "OI",
      "region": "Condiciones de clima, suelo y altitud, en una o dos frases.",
      "siembra": {"texto": "Ventana de siembra tal como la da la agenda.", "meses": [10, 11]},
      "variedades": ["..."],
      "hibridos_comerciales": ["..."],
      "densidad": "Semilla por ha o plantas por metro/ha.",
      "fertilizacion": "Fórmula y momento de aplicación.",
      "riego": "Número y momento de riegos, etapas críticas.",
      "plagas": ["Nombres de las plagas principales"],
      "enfermedades": ["Nombres de las enfermedades principales"],
      "malezas": "Periodo crítico y control cultural o mecánico, sin productos.",
      "cosecha": "Indicador de madurez, humedad del grano, días.",
      "cuidados": ["4 a 6 recomendaciones prácticas, las más importantes de la ficha"],
      "costos": [
        {"modalidad": "riego", "costo_total_ha": 19479, "rendimiento": 900, "unidad_rendimiento": "kg/ha",
         "precio": 25, "ingreso_neto": 3021, "relacion_bc": 1.16}
      ],
      "nota": null,
      "revisado": false
    }
  ]
}
```

Detalle de campos:

- `modalidad`: `"riego"`, `"temporal"` o `null` si la ficha cubre ambas. Deducir del nombre
  ("Maíz de riego") o del `regimen_hidrico`.
- `ciclo`: `"OI"` (Otoño-Invierno), `"PV"` (Primavera-Verano), `"PER"` (perenne) o `null`. Deducir
  de la fecha de siembra y del tipo de cultivo.
- `siembra.meses`: enteros 1–12 de la ventana recomendada (p. ej. "15 de octubre al 20 de
  noviembre" → `[10, 11]`). Para perennes, los meses de plantación. `[]` si no hay fecha.
- `costos`: cada cuadro del extraído trae valores parseados por reglas (**son solo una pista**,
  fallan seguido) y `texto`, la tabla cruda. Toma los valores de `texto` (o del texto de la
  ficha, sobre todo el rendimiento esperado en `cosecha`) y copia **solo los que puedas
  confirmar** y que sean coherentes: ingreso_neto ≈ ingreso_bruto − costo_total y relacion_bc ≈
  ingreso_bruto / costo_total. Los cuadros impresos del INIFAP a veces traen errores de suma: si
  un valor no cuadra, ponlo en `null` y explícalo en `nota`. Si el cuadro trae un costo de
  establecimiento y otro de mantenimiento (frutales), usa el de mantenimiento o producción plena
  e indícalo en `nota`. Añade `unidad_rendimiento` (kg/ha o t/ha). `[]` si no hay cuadro.
- `variedades`: variedades públicas (INIFAP, criollas, de dominio público).
- `hibridos_comerciales`: híbridos y variedades comerciales de empresas privadas que la agenda
  recomienda o evaluó (tablas de híbridos, listas de materiales). Uno por elemento, con la empresa
  entre paréntesis si el texto la da: `"DK-4050 (Dekalb)"`. Solo nombres, sin juicios de calidad
  que no estén en el texto. `[]` si la ficha no menciona ninguno. Esto es distinto de los
  plaguicidas: los nombres de híbridos sí van; las marcas y dosis de plaguicidas siguen prohibidas.
- Si el `tipo_cultivo` o el `regimen_hidrico` declarados contradicen el texto (p. ej. un cultivo de
  ciclo marcado como "perenne"), corrige según el texto y explícalo en `nota`.
- Fichas que no son un cultivo (p. ej. una entrada "Otoño-Invierno" o "Temperatura" que se coló
  del índice): omítelas y menciónalas en el reporte final.

Al terminar, valida el archivo con Python: JSON válido, `cultivo_ids` existentes en el catálogo y
`siembra.meses` con enteros 1–12.
