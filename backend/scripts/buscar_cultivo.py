"""Elige el punto de campo de cada estado: el píxel de CULTIVO más cercano a la capital según el
mapa de cobertura de NASA MODIS (MCD12Q1 v061, 500 m, clases IGBP 12 "cultivo" y 14 "mosaico de
cultivo y vegetación natural"). Escribe los puntos en services/municipios.py (lat_suelo, lon_suelo).

Se pide una ventana alrededor de la capital (primero ~25 km, si no hay cultivo ~50 km) en UNA
consulta por estado.

    docker compose exec backend python -m scripts.buscar_cultivo
"""

import asyncio
import math
import re
from datetime import date
from pathlib import Path

import httpx

from app.services.municipios import MUNICIPIOS
from app.services.suelo import modis

ARCHIVO = Path(modis.__file__).resolve().parents[1] / "municipios.py"
RADIOS = [50, 100]  # en píxeles de 500 m: ~25 km y ~50 km
CULTIVO = (12, 14)
N = 2400


def lat_lon_de_pixel(h: int, v: int, fila: int, col: int) -> tuple[float, float]:
    celda = modis._MOSAICO / N
    x = modis._X0 + h * modis._MOSAICO + (col + 0.5) * celda
    y = modis._Y0 - v * modis._MOSAICO - (fila + 0.5) * celda
    lat = math.degrees(y / modis._R)
    lon = math.degrees(x / (modis._R * math.cos(math.radians(lat))))
    return round(lat, 4), round(lon, 4)


async def buscar(cliente: httpx.AsyncClient, m) -> tuple[float, float, float, int] | None:
    h, v, fila, col = modis.pixel_sinusoidal(m.lat, m.lon, N)
    hoy = date.today()
    granulos = await modis._granulos(cliente, modis.COLECCION_LC, m.lat, m.lon, f"h{h:02d}v{v:02d}",
                                     f"{hoy.year - 4}-01-01", hoy.isoformat())
    granulo = granulos[max(granulos)]
    for radio in RADIOS:
        f0, f1 = max(0, fila - radio), min(N - 1, fila + radio)
        c0, c1 = max(0, col - radio), min(N - 1, col + radio)
        r = await cliente.get(
            modis.OPENDAP.format(c=modis.COLECCION_LC, g=granulo),
            params={"dap4.ce": f"{modis.VAR_LC}[{f0}:1:{f1}][{c0}:1:{c1}]"},
            headers={"Authorization": f"Bearer {modis._token()}"},
        )
        r.raise_for_status()
        filas = [ln.partition(",")[2] for ln in r.text.splitlines()[1:] if "[" in ln]
        mejor = None
        for i, linea in enumerate(filas):
            for j, valor in enumerate(linea.split(",")):
                if valor.strip() and int(float(valor)) in CULTIVO:
                    d = math.hypot(f0 + i - fila, c0 + j - col)
                    if mejor is None or d < mejor[0]:
                        mejor = (d, f0 + i, c0 + j, int(float(valor)))
        if mejor:
            lat, lon = lat_lon_de_pixel(h, v, mejor[1], mejor[2])
            return lat, lon, mejor[0] * 0.463, mejor[3]  # 0.463 km por píxel
    return None


async def main() -> None:
    texto = ARCHIVO.read_text(encoding="utf-8")
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as cliente:
        semaforo = asyncio.Semaphore(6)

        async def uno(m):
            async with semaforo:
                try:
                    return m, await buscar(cliente, m)
                except Exception as e:  # noqa: BLE001
                    return m, e

        resultados = await asyncio.gather(*(uno(m) for m in MUNICIPIOS))

    for m, res in resultados:
        if not isinstance(res, tuple):
            print(f"{m.nombre}: NO se encontró cultivo ({res})")
            continue
        lat, lon, km, clase = res
        nombre = re.escape(m.nombre)
        patron = re.compile(r'(Municipio\("' + nombre + r'", [-\d.]+, [-\d.]+, "[^"]+", )[-\d.]+, [-\d.]+\),[^\n]*')
        assert patron.search(texto), m.nombre
        tipo = "cultivo" if clase == 12 else "mosaico de cultivo"
        texto = patron.sub(lambda mm: f"{mm.group(1)}{lat}, {lon}),  # {tipo} MODIS a ~{km:.0f} km de la capital", texto)
        print(f"{m.nombre}: {lat}, {lon} ({tipo}, ~{km:.0f} km de la capital)")
    ARCHIVO.write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
