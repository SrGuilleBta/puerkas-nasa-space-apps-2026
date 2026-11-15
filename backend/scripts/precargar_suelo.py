"""Precarga los datos lentos del módulo Suelo para los 32 estados, para que la app (y el demo)
respondan rápido:

- SMAP: últimos 30 días + el mismo periodo de cada año desde 2015 (~330 días por estado, ~1.5 min
  la primera vez). Queda en backend/data/suelo/smap/.
- SRTM: el mosaico de terreno de cada estado (~25 MB cada uno). Queda en backend/data/srtm/.
- MODIS: NDVI de los últimos 3 años (~3 min por estado, el servicio es lento). Queda en
  backend/data/suelo/modis/.

Se puede correr otra vez cuando sea: lo que ya está guardado no se vuelve a bajar (solo los días
nuevos de SMAP).

    docker compose exec backend python -m scripts.precargar_suelo
"""

import asyncio
import time

from app.services.municipios import MUNICIPIOS
from app.services.suelo import modis, smap, srtm


async def main() -> None:
    inicio_total = time.monotonic()
    for i, m in enumerate(MUNICIPIOS, 1):
        t = time.monotonic()
        partes = []
        try:
            e = await smap.estado_sequia(m.lat_suelo, m.lon_suelo)
            partes.append(f"SMAP: {e.get('categoria') or ''} {e.get('estado') or e.get('mensaje')}")
        except Exception as ex:  # noqa: BLE001 - se reporta y se sigue con el siguiente estado
            partes.append(f"SMAP falló: {ex}")
        try:
            terreno = await srtm.terreno(m.lat_suelo, m.lon_suelo)
            partes.append(f"SRTM: pendiente {terreno['pendiente_promedio_pct']} %")
        except Exception as ex:  # noqa: BLE001
            partes.append(f"SRTM falló: {ex}")
        try:
            c = await modis.cobertura(m.lat_suelo, m.lon_suelo)
            partes.append(f"MODIS: menor cobertura en {(c['mes_menor_cobertura'] or {}).get('mes')}")
        except Exception as ex:  # noqa: BLE001
            partes.append(f"MODIS falló: {ex}")
        print(f"[{i}/{len(MUNICIPIOS)}] {m.nombre} ({time.monotonic() - t:.0f} s) · " + " · ".join(partes), flush=True)
    print(f"Listo en {(time.monotonic() - inicio_total) / 60:.0f} min", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
