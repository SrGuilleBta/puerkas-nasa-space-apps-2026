# Instrucciones para traducir al inglés los JSON de Cultivos

Los datos de Cultivos que la app muestra están en **inglés**. Esto aplica a los resúmenes INIFAP
(`backend/data/inifap/cuidados/<estado>.json`) y a `backend/pipeline/cultivos/curado.json`. Lo que
la pipeline genera al arrancar se traduce solo, con plantillas en inglés y
[glosario_en.json](glosario_en.json).

## Reglas

1. **Traduce, no reescribas.** Mismo contenido, mismo nivel de detalle, mismas cifras y unidades.
   No agregues ni quites información. Inglés claro y técnico para productores y técnicos.
2. **Las llaves del JSON no se traducen.** Solo los valores de texto.
3. **Usa la terminología de [glosario_en.json](glosario_en.json)**: la sección `terminos` (temporal →
   *rainfed*, riego de auxilio → *supplemental irrigation*, acame → *lodging*, gusano cogollero → *fall
   armyworm*...) y la sección `cultivos` para los nombres de cultivo.
4. **No se traducen:**
   - Códigos e ids: `cve_ent`, `cultivo_ids`, `ciclo` (`OI`, `PV`, `PER`), `eppocode`.
   - Números y listas numéricas: `paginas`, `siembra.meses`, todos los valores de `costos`.
   - `revisado`, `edicion` y los nombres científicos (`cientifico`, y los binomios latinos dentro del texto).
   - Los nombres propios: variedades, híbridos, empresas, lugares (estados, valles, regiones,
     municipios) e instituciones (INIFAP, SIAP, FIRA).
5. **Valores con traducción fija:**
   - `modalidad` (también dentro de `costos`): `riego` → `irrigated`, `temporal` → `rainfed`; `null` se queda.
   - `tipo_cultivo`: `anual` → `annual`, `perenne` → `perennial`.
   - `estado`: solo cambia `Estado de México` → `State of Mexico`.
   - `unidad_rendimiento`: `kg/ha` y `t/ha` se quedan; `frutos/ha` → `fruits/ha`,
     `piezas/ha` → `pieces/ha`, `pacas/ha` → `bales/ha`, `plantas/m2` → `plants/m2`.
   - `fuente`: deja el título del documento en español y agrega su traducción entre corchetes:
     `INIFAP. Agenda Técnica Agrícola de Sinaloa [Agricultural Technical Agenda of Sinaloa]. INIFAP, Mexico City, 2026.`
6. Traduce también `_nota` y `nota`.
7. Formato: `json.dump(..., ensure_ascii=False, indent=2)`.

## Validación

Desde `backend/`:

```bash
python -m pipeline.cultivos.validar_traduccion ORIGINAL_ES.json TRADUCIDO_EN.json
```

El validador revisa estructura, números, campos de código y valores fijos, y marca textos que
parecen seguir en español. Debe terminar con **0 errores**. Revisa los avisos uno por uno; algunos
son falsos positivos (nombres propios en español).
