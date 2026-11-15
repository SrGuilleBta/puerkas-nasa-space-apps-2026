"""Descarga las fuentes complementarias a SIAP.

Los CSV de SIAP ya están en el repo (ver backend/data/siap/README.md). Esto baja:
- Monitor de Sequía de México por municipio (CONAGUA/SMN), quincenal desde 2003.
- Tabla EcoCrop (FAO), rangos agronómicos de ~2,500 cultivos.
- Inflación promedio anual de México (FMI) para deflactar el precio medio rural.
"""

import csv
import json
import urllib.request
from datetime import date

from . import config


def _bajar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "cultivos-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _guardar(ruta, contenido: bytes):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    print(f"  {ruta.relative_to(config.BACKEND_DIR)} ({len(contenido) / 1e6:.1f} MB)")


def descargar_sequia():
    _guardar(config.SEQUIA_XLSX, _bajar(config.URL_SEQUIA))


def descargar_ecocrop():
    _guardar(config.ECOCROP_CSV, _bajar(config.URL_ECOCROP))


def descargar_inflacion():
    """Actualiza el CSV de inflación. El CSV ya está en el repo; si el FMI rechaza la
    petición (a veces responde 403 a clientes que no son navegador), se conserva el
    actual y basta con agregar a mano la fila del año nuevo."""
    try:
        datos = json.loads(_bajar(config.URL_INFLACION))
    except Exception as e:  # noqa: BLE001
        print(f"  inflación: no se pudo descargar ({e}); se conserva {config.INFLACION_CSV.name}")
        return
    serie = datos["values"]["PCPIPCH"]["MEX"]
    # El WEO trae proyecciones; solo se guardan años ya cerrados.
    anios = [a for a in sorted(serie) if int(a) < date.today().year]
    config.INFLACION_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(config.INFLACION_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["anio", "inflacion_promedio_pct"])
        for anio in anios:
            w.writerow([anio, serie[anio]])
    print(f"  {config.INFLACION_CSV.relative_to(config.BACKEND_DIR)} ({len(anios)} años)")


def descargar_todo():
    print("Descargando fuentes:")
    descargar_sequia()
    descargar_ecocrop()
    descargar_inflacion()
