"""Genera la tabla fija de SoilGrids por municipio (módulo Suelo).

Consulta SoilGrids UNA vez por cada punto de campo de services/municipios.py (lat_suelo/lon_suelo)
y guarda el resultado en backend/data/suelo/soilgrids_municipios.json. Así la app no depende de
SoilGrids mientras se usa (es lento y limita a ~5 consultas por minuto).

Correr de nuevo solo cuando se agreguen municipios. Los puntos que ya están en la tabla se saltan.

    docker compose exec backend python -m scripts.generar_suelo_municipios

Opciones:
    --todo     vuelve a consultar también los puntos que ya están en la tabla
"""

import asyncio
import json
import sys

from app.services.municipios import MUNICIPIOS
from app.services.suelo import soilgrids

ESPERA_SEGUNDOS = 13  # ~4-5 consultas por minuto, debajo del límite de SoilGrids
REINTENTOS = 3


async def main(todo: bool) -> None:
    tabla = {}
    if soilgrids.TABLA.exists():
        tabla = json.loads(soilgrids.TABLA.read_text(encoding="utf-8")).get("puntos", {})

    pendientes = [m for m in MUNICIPIOS if todo or soilgrids.clave_punto(m.lat_suelo, m.lon_suelo) not in tabla]
    print(f"{len(MUNICIPIOS)} municipios, {len(pendientes)} por consultar")

    fallidos = []
    for i, m in enumerate(pendientes, 1):
        clave = soilgrids.clave_punto(m.lat_suelo, m.lon_suelo)
        for intento in range(1, REINTENTOS + 1):
            try:
                datos = await soilgrids.consultar_soilgrids(m.lat_suelo, m.lon_suelo)
                if all(v.get("phh2o") is None for v in datos.values()):
                    # No se guarda: puede ser un punto sin dato o una respuesta mala de SoilGrids
                    # saturado. Se vuelve a intentar la próxima vez que se corra el script.
                    print(f"[{i}/{len(pendientes)}] {m.nombre}: SoilGrids regresó vacío (no se guardó)")
                    break
                tabla[clave] = {"municipio": m.nombre, "lat": m.lat_suelo, "lon": m.lon_suelo, "datos": datos}
                print(f"[{i}/{len(pendientes)}] {m.nombre}: ok")
                break
            except RuntimeError:
                print(f"[{i}/{len(pendientes)}] {m.nombre}: SoilGrids no respondió (intento {intento}/{REINTENTOS})")
                await asyncio.sleep(ESPERA_SEGUNDOS * 2)
        else:
            fallidos.append(m.nombre)

        # Se guarda después de cada punto: si se corta, no se pierde lo avanzado
        soilgrids.guardar_tabla(tabla)
        if i < len(pendientes):
            await asyncio.sleep(ESPERA_SEGUNDOS)

    print(f"Listo: {len(tabla)} puntos en {soilgrids.TABLA}")
    if fallidos:
        print("No se pudieron consultar (corre el script otra vez):", ", ".join(fallidos))


if __name__ == "__main__":
    asyncio.run(main(todo="--todo" in sys.argv))
