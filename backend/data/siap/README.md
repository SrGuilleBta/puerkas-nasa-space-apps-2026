# SIAP — Cierre de la Producción Agrícola (nivel municipal)

Fuente: [SIAP, Datos abiertos agrícolas](https://nube.agricultura.gob.mx/datosAbiertos/Agricola.php).
Descargado el 2026-11-14. Un archivo por año, 2015–2025 (~61 MB en total).

Descarga de otro año (el `view` es el mismo para 2003–2025; 2001 y 2002 usan otro):

```bash
curl -L -o cierre_agricola_mun_2014.csv \
  "https://nube.agricultura.gob.mx/index.php?view=10AE434F-A2158368-A120BC5A-EDF4AFAA&ANIO=2014"
```

## Formato

- Codificación **ISO-8859-1** (no UTF-8). En pandas: `pd.read_csv(f, encoding="latin1")`.
- Una fila por año × municipio × ciclo × modalidad × cultivo (~37 mil filas por año).
- Columnas: `Anio, Idestado, Nomestado, Idddr, Nomddr, Idcader, Nomcader, Idmunicipio,
  Nommunicipio, Idciclo, Nomcicloproductivo, Idmodalidad, Nommodalidad, Idunidadmedida,
  Nomunidad, Idcultivo, Nomcultivo, Sembrada, Cosechada, Siniestrada, Volumenproduccion,
  Rendimiento, Preciomediorural, Valorproduccion`.
- `Preciomediorural` es precio al productor (pesos por unidad de `Nomunidad`), no de mayoreo.
- Ciclos: Otoño-Invierno, Primavera-Verano, Perennes. Modalidad: Riego o Temporal.
- Diccionario oficial de campos: en la misma página de SIAP.

## En Docker

El `Dockerfile` copia `backend/data` a `/code/data`, así que dentro del contenedor los archivos
están en `/code/data/siap/`. Desde el código: `Path(__file__).resolve().parent.parent / "data" / "siap"`
(mismo patrón que `static` en `app/main.py`). Tras añadir o cambiar CSV hay que reconstruir:
`docker compose up --build -d`.
