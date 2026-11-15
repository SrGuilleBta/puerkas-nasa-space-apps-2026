"""Elevación y pendiente del terreno con NASA SRTM (SRTMGL1, 30 m).

- Se descarga el mosaico de 1°×1° que contiene el punto (≈25 MB, una sola vez) y se guarda en
  backend/data/srtm/ (está en .gitignore).
- Requiere EARTHDATA_TOKEN en .env.
- El archivo .hgt es una cuadrícula de 3601×3601 enteros de 16 bits (big-endian); -32768 = sin dato.
"""

import asyncio
import math
import os
import struct
import zipfile
from pathlib import Path

import httpx

URL = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL1.003/{t}.SRTMGL1.hgt/{t}.SRTMGL1.hgt.zip"
CARPETA = Path(__file__).resolve().parents[3] / "data" / "srtm"
N = 3601
SIN_DATO = -32768
METROS_POR_GRADO = 111_320

_bloqueo = asyncio.Lock()


def _nombre_mosaico(lat: float, lon: float) -> tuple[str, int, int]:
    lat0, lon0 = math.floor(lat), math.floor(lon)
    ns = f"N{lat0:02d}" if lat0 >= 0 else f"S{-lat0:02d}"
    ew = f"E{lon0:03d}" if lon0 >= 0 else f"W{-lon0:03d}"
    return ns + ew, lat0, lon0


async def _asegurar_mosaico(nombre: str) -> Path:
    hgt = CARPETA / f"{nombre}.hgt"
    if hgt.exists():
        return hgt
    token = os.getenv("EARTHDATA_TOKEN")
    if not token:
        raise RuntimeError("EARTHDATA_TOKEN is missing in .env (needed for SRTM)")
    async with _bloqueo:
        if hgt.exists():
            return hgt
        CARPETA.mkdir(parents=True, exist_ok=True)
        zip_path = CARPETA / f"{nombre}.zip"
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as cliente:
            r = await cliente.get(URL.format(t=nombre), headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 404:
                raise FileNotFoundError(f"SRTM has no tile {nombre} (probably sea)")
            r.raise_for_status()
            zip_path.write_bytes(r.content)
        with zipfile.ZipFile(zip_path) as z:
            interno = next(n for n in z.namelist() if n.endswith(".hgt"))
            hgt.write_bytes(z.read(interno))
        zip_path.unlink()
    return hgt


def _leer_ventana(hgt: Path, fila0: int, col0: int, filas: int, cols: int) -> list[list[int]]:
    ventana = []
    with open(hgt, "rb") as f:
        for i in range(filas):
            f.seek(((fila0 + i) * N + col0) * 2)
            ventana.append(list(struct.unpack(f">{cols}h", f.read(cols * 2))))
    return ventana


async def terreno(lat: float, lon: float, radio_celdas: int = 3) -> dict:
    """Elevación del punto y pendiente promedio/máxima en una ventana de ~(2·radio+1)×30 m."""
    nombre, lat0, lon0 = _nombre_mosaico(lat, lon)
    hgt = await _asegurar_mosaico(nombre)

    fila = round((lat0 + 1 - lat) * (N - 1))
    col = round((lon - lon0) * (N - 1))
    r = radio_celdas + 1  # una celda extra para calcular pendiente en el borde
    fila0, col0 = max(0, fila - r), max(0, col - r)
    filas, cols = min(N, fila + r + 1) - fila0, min(N, col + r + 1) - col0
    z = _leer_ventana(hgt, fila0, col0, filas, cols)

    dy = METROS_POR_GRADO / (N - 1)
    dx = dy * math.cos(math.radians(lat))
    pendientes = []
    for i in range(1, filas - 1):
        for j in range(1, cols - 1):
            vecinos = [z[i + a][j + b] for a in (-1, 0, 1) for b in (-1, 0, 1)]
            if SIN_DATO in vecinos:
                continue
            # Método de Horn (3×3)
            dzdx = ((z[i-1][j+1] + 2*z[i][j+1] + z[i+1][j+1]) - (z[i-1][j-1] + 2*z[i][j-1] + z[i+1][j-1])) / (8 * dx)
            dzdy = ((z[i+1][j-1] + 2*z[i+1][j] + z[i+1][j+1]) - (z[i-1][j-1] + 2*z[i-1][j] + z[i-1][j+1])) / (8 * dy)
            pendientes.append(math.hypot(dzdx, dzdy) * 100)  # en %

    elevacion = z[fila - fila0][col - col0]
    return {
        "elevacion_m": None if elevacion == SIN_DATO else elevacion,
        "pendiente_promedio_pct": round(sum(pendientes) / len(pendientes), 1) if pendientes else None,
        "pendiente_maxima_pct": round(max(pendientes), 1) if pendientes else None,
        "area_analizada_m": round((2 * radio_celdas + 1) * dy),
        "mosaico": nombre,
    }


async def factor_ls(lat: float, lon: float, radio_cuenca: int = 60, radio_punto: int = 3) -> dict:
    """Factor topográfico LS de la RUSLE (Ecuación Universal de Pérdida de Suelo Revisada, USDA)
    calculado con el modelo de elevación, con la fórmula de Moore y Burch (1986):

        LS = (As / 22.13)^0.4 × (sin β / 0.0896)^1.3

    As = área de captación específica (agua que llega a cada celda desde cuesta arriba, con el método
    de flujo D8: cada celda descarga a su vecina más baja), β = pendiente (método de Horn).
    LS = 1 equivale a la parcela estándar de la RUSLE (22.13 m de largo, 9 % de pendiente); un valor
    de 3 significa ~3 veces más pérdida de suelo por la forma del terreno, con todo lo demás igual.

    Se analiza una ventana de ~(2·radio_cuenca+1)×30 m (~3.6 km) y se reporta el LS de las celdas
    centrales. El agua que viene de fuera de la ventana no se cuenta (puede subestimar LS en laderas
    muy largas).
    """
    nombre, lat0, lon0 = _nombre_mosaico(lat, lon)
    hgt = await _asegurar_mosaico(nombre)

    fila = round((lat0 + 1 - lat) * (N - 1))
    col = round((lon - lon0) * (N - 1))
    r = radio_cuenca + 1
    fila0, col0 = max(0, fila - r), max(0, col - r)
    filas, cols = min(N, fila + r + 1) - fila0, min(N, col + r + 1) - col0
    z = _leer_ventana(hgt, fila0, col0, filas, cols)

    dy = METROS_POR_GRADO / (N - 1)
    dx = dy * math.cos(math.radians(lat))
    celda = math.sqrt(dx * dy)
    vecinos = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]

    # Pendiente (Horn) y dirección de flujo D8 de cada celda interior
    sen_beta: dict[tuple[int, int], float] = {}
    destino: dict[tuple[int, int], tuple[int, int]] = {}
    for i in range(1, filas - 1):
        for j in range(1, cols - 1):
            ventana = [z[i + a][j + b] for a in (-1, 0, 1) for b in (-1, 0, 1)]
            if SIN_DATO in ventana:
                continue
            dzdx = ((z[i-1][j+1] + 2*z[i][j+1] + z[i+1][j+1]) - (z[i-1][j-1] + 2*z[i][j-1] + z[i+1][j-1])) / (8 * dx)
            dzdy = ((z[i+1][j-1] + 2*z[i+1][j] + z[i+1][j+1]) - (z[i-1][j-1] + 2*z[i-1][j] + z[i-1][j+1])) / (8 * dy)
            sen_beta[(i, j)] = math.sin(math.atan(math.hypot(dzdx, dzdy)))
            mejor, caida_max = None, 0.0
            for a, b in vecinos:
                distancia = math.hypot(a * dy, b * dx)
                caida = (z[i][j] - z[i + a][j + b]) / distancia
                if caida > caida_max:
                    mejor, caida_max = (i + a, j + b), caida
            if mejor is not None:
                destino[(i, j)] = mejor

    # Acumulación de flujo: de la celda más alta a la más baja, cada una pasa lo que lleva a su destino
    acumulado = {c: 1.0 for c in sen_beta}
    for c in sorted(sen_beta, key=lambda c: z[c[0]][c[1]], reverse=True):
        d = destino.get(c)
        if d in acumulado:
            acumulado[d] += acumulado[c]

    centro = (fila - fila0, col - col0)
    valores = []
    for a in range(-radio_punto, radio_punto + 1):
        for b in range(-radio_punto, radio_punto + 1):
            c = (centro[0] + a, centro[1] + b)
            if c in sen_beta:
                area_especifica = acumulado[c] * celda
                valores.append((area_especifica / 22.13) ** 0.4 * (sen_beta[c] / 0.0896) ** 1.3)
    return {
        "ls_promedio": round(sum(valores) / len(valores), 2) if valores else None,
        "ls_maximo": round(max(valores), 2) if valores else None,
        "area_analizada_m": round((2 * radio_punto + 1) * dy),
        "metodo": "Factor LS de la RUSLE con modelo de elevación (Moore y Burch, 1986): (As/22.13)^0.4 × (sen β/0.0896)^1.3; flujo D8",
        "referencia": "LS = 1 equals the standard RUSLE plot (22.13 m long, 9 % slope)",
    }
