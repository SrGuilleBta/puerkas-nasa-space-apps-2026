"""Mejor época para sembrar un cultivo en un lugar.

Compara el rango de temperatura del cultivo (catálogo de Cultivos, EcoCrop) con el clima promedio
de cada mes en ese lugar (NASA POWER). Cada mes del ciclo recibe un puntaje de 1 (dentro de la
temperatura ideal) que baja de forma lineal hasta 0 en el límite que el cultivo tolera; el puntaje
de un mes de siembra es el promedio de los meses que dura su ciclo:

- "good": 0.85 o más y todos los meses dentro de lo tolerable.
- "fair": 0.55 o más y todos los meses dentro de lo tolerable.
- "poor": el resto, o algún mes fuera del rango tolerable.

Es una guía por promedios mensuales (no ve heladas ni olas de calor puntuales ni las variedades
regionales) y no sabe si hay riego: por eso avisa cuando la lluvia del ciclo queda por debajo de lo
que el cultivo prefiere.
"""

import math

from app.services.catalogo_cultivos import ciclo_de

UMBRAL_GOOD = 0.85
UMBRAL_FAIR = 0.55


def _puntaje_mes(t: float, ideal: list[float], absoluta: list[float] | None) -> float:
    """1 dentro del rango ideal; baja linealmente hasta 0 en el límite tolerable; 0 fuera de él."""
    if ideal[0] <= t <= ideal[1]:
        return 1.0
    if absoluta is None:
        return 0.0
    if t < ideal[0]:
        return max(0.0, (t - absoluta[0]) / (ideal[0] - absoluta[0])) if ideal[0] > absoluta[0] else 0.0
    return max(0.0, (absoluta[1] - t) / (absoluta[1] - ideal[1])) if absoluta[1] > ideal[1] else 0.0


def calcular(ficha: dict, temp: list[float], lluvia_mm: list[float]) -> dict:
    """`ficha` es una ficha del catálogo; `temp` y `lluvia_mm` traen 12 valores (enero a diciembre)."""
    ideal = ficha.get("temperatura_optima_c")
    if ficha.get("perenne") or not ideal:
        # Un frutal o un pasto perenne no tiene "mes de siembra": el cálculo no aplica
        return {"estacional": False, "meses": [], "mejores": []}

    absoluta = ficha.get("temperatura_absoluta_c")
    lluvia_ideal = (ficha.get("agua") or {}).get("lluvia_optima_mm")
    duracion = min(12, max(1, math.ceil(ciclo_de(ficha) / 30.4)))

    meses = []
    for inicio in range(12):
        indices = [(inicio + i) % 12 for i in range(duracion)]
        temperaturas = [temp[i] for i in indices]
        puntaje = sum(_puntaje_mes(t, ideal, absoluta) for t in temperaturas) / duracion
        fuera_de_lo_tolerable = absoluta is not None and any(not (absoluta[0] <= t <= absoluta[1]) for t in temperaturas)
        if fuera_de_lo_tolerable or puntaje < UMBRAL_FAIR:
            nivel = "poor"
        else:
            nivel = "good" if puntaje >= UMBRAL_GOOD else "fair"
        lluvia = round(sum(lluvia_mm[i] for i in indices))
        meses.append({
            "mes": inicio + 1,
            "nivel": nivel,
            "puntaje": round(puntaje, 2),
            "tempMedia": round(sum(temperaturas) / duracion, 1),
            "lluviaMm": lluvia,
            "necesitaRiego": bool(lluvia_ideal) and lluvia < lluvia_ideal[0],
        })

    for nivel in ("good", "fair"):
        mejores = [m["mes"] for m in meses if m["nivel"] == nivel]
        if mejores:
            break
    return {
        "estacional": True,
        "mesesDelCiclo": duracion,
        "temperaturaIdealC": ideal,
        "meses": meses,
        "mejores": mejores,
        "nivelMejores": nivel if mejores else None,
        "fuente": "NASA POWER (monthly climate) and the crop's ideal temperature from EcoCrop",
    }
