"""Tendencia de agua almacenada en la región con GRACE / GRACE-FO (JPL Mascon RL06.3 CRI).

- Mide el agua TOTAL almacenada (subterránea + humedad del suelo + superficial + nieve), como
  anomalía en cm de agua equivalente respecto al promedio 2004-2009.
- Resolución muy gruesa (mascons de ~300 km; cuadrícula de 0.5°): solo sirve como tendencia regional.
- Un solo archivo NetCDF (~46 MB) con toda la serie desde 2002. Se descarga una vez a
  backend/data/grace/ (está en .gitignore). Requiere EARTHDATA_TOKEN en .env.
"""

import asyncio
import os
from datetime import date, timedelta
from pathlib import Path

import h5py
import httpx

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLECCION = "C3195527175-POCLOUD"  # TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4
CARPETA = Path(__file__).resolve().parents[3] / "data" / "grace"

_bloqueo = asyncio.Lock()


async def _asegurar_archivo() -> Path:
    existentes = sorted(CARPETA.glob("GRCTellus*.nc"))
    if existentes:
        return existentes[-1]
    token = os.getenv("EARTHDATA_TOKEN")
    if not token:
        raise RuntimeError("Falta EARTHDATA_TOKEN en .env para descargar GRACE")
    async with _bloqueo:
        existentes = sorted(CARPETA.glob("GRCTellus*.nc"))
        if existentes:
            return existentes[-1]
        async with httpx.AsyncClient(timeout=600, follow_redirects=True) as cliente:
            r = await cliente.get(CMR, params={"collection_concept_id": COLECCION, "sort_key": "-start_date", "page_size": 1})
            r.raise_for_status()
            granulo = r.json()["feed"]["entry"][0]
            url = next(l["href"] for l in granulo["links"] if l["href"].startswith("https") and l["href"].endswith(".nc"))
            r = await cliente.get(url, headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
        CARPETA.mkdir(parents=True, exist_ok=True)
        destino = CARPETA / url.rsplit("/", 1)[-1]
        destino.write_bytes(r.content)
        return destino


def _tendencia_por_anio(x: list[float], y: list[float]) -> float:
    """Pendiente de mínimos cuadrados (y por unidad de x)."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = sum((a - mx) ** 2 for a in x)
    return num / den


def _leer_serie(archivo: Path, lat: float, lon: float) -> dict:
    with h5py.File(archivo, "r") as f:
        lats, lons = f["lat"][:], f["lon"][:]
        lon360 = lon % 360
        i = int(abs(lats - lat).argmin())
        j = int(abs(lons - lon360).argmin())
        lwe = f["lwe_thickness"][:, i, j]
        relleno = f["lwe_thickness"].attrs.get("_FillValue")
        tiempos = f["time"][:]
        unidades = f["time"].attrs["units"]
        unidades = unidades.decode() if isinstance(unidades, bytes) else unidades
    base = date.fromisoformat(unidades.split("since")[1].strip()[:10])
    serie = []
    for t, v in zip(tiempos, lwe):
        if relleno is not None and v == relleno:
            continue
        serie.append({"fecha": (base + timedelta(days=float(t))).isoformat(), "anomalia_cm": round(float(v), 2)})
    return {"serie": serie, "celda_lat": float(lats[i]), "celda_lon": float(lons[j]) - (360 if lons[j] > 180 else 0)}


async def agua_subterranea(lat: float, lon: float) -> dict:
    archivo = await _asegurar_archivo()
    datos = await asyncio.to_thread(_leer_serie, archivo, lat, lon)
    serie = datos["serie"]
    anios = [date.fromisoformat(p["fecha"]).toordinal() / 365.25 for p in serie]
    tendencia = round(_tendencia_por_anio(anios, [p["anomalia_cm"] for p in serie]), 2)
    if tendencia < 0:
        lectura = "La región está perdiendo agua almacenada"
    elif tendencia > 0:
        lectura = "La región está ganando agua almacenada"
    else:
        lectura = "Sin cambio claro en el agua almacenada"
    return {
        "tendencia_cm_por_anio": tendencia,
        "lectura": lectura,
        "ultimo_dato": serie[-1] if serie else None,
        "serie": serie,
        "celda": {"lat": datos["celda_lat"], "lon": datos["celda_lon"]},
        "nota": "Agua total almacenada (subterránea + suelo + superficial), anomalía vs. 2004-2009. Resolución ~300 km: tendencia regional, no de la parcela.",
        "fuente": f"NASA GRACE/GRACE-FO JPL Mascon RL06.3 ({archivo.name})",
    }
