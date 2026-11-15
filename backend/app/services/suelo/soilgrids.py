"""Propiedades del suelo de SoilGrids (ISRIC): pH, arcilla, arena, limo y carbono orgánico.

Notas de la fuente:
- Resolución 250 m, global, sin llave.
- Valores escalados: pH viene x10; arcilla/arena/limo en g/kg (÷10 = %); carbono orgánico (soc) en dg/kg (÷10 = g/kg).
- En zonas urbanas devuelve null: usar coordenadas de campo.

Tabla fija por municipio: como el suelo no cambia (SoilGrids es un mapa fijo), los puntos de campo
de cada municipio se consultan UNA vez con `python -m scripts.generar_suelo_municipios` y se guardan
en backend/data/suelo/soilgrids_municipios.json (sí se sube al repo). La app lee de ahí y solo
consulta SoilGrids en vivo si el punto no está en la tabla.
"""

import asyncio
import json
from datetime import date
from pathlib import Path

import httpx

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPIEDADES = ["phh2o", "clay", "sand", "silt", "soc"]
PROFUNDIDADES = ["0-5cm", "5-15cm", "15-30cm"]  # zona de raíces
FACTOR_VAN_BEMMELEN = 1.724
TABLA = Path(__file__).resolve().parents[3] / "data" / "suelo" / "soilgrids_municipios.json"

_cache: dict[tuple, dict] = {}
_tabla: dict | None = None
_bloqueo = asyncio.Lock()


def clave_punto(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def _leer_tabla() -> dict:
    """Puntos ya consultados: {"lat,lon": {"municipio": ..., "datos": {profundidad: {propiedad: valor}}}}."""
    global _tabla
    if _tabla is None:
        _tabla = json.loads(TABLA.read_text(encoding="utf-8"))["puntos"] if TABLA.exists() else {}
    return _tabla


def textura_usda(arena: float, limo: float, arcilla: float) -> str:
    """Clase de textura según el triángulo de texturas del USDA (porcentajes)."""
    s, l, a = arena, limo, arcilla
    if l + 1.5 * a < 15:
        return "sand"
    if l + 2 * a < 30:
        return "loamy sand"
    if (7 <= a < 20 and s > 52) or (a < 7 and l < 50):
        return "sandy loam"
    if 7 <= a < 27 and 28 <= l < 50 and s <= 52:
        return "loam"
    if (l >= 50 and 12 <= a < 27) or (50 <= l < 80 and a < 12):
        return "silt loam"
    if l >= 80 and a < 12:
        return "silt"
    if 20 <= a < 35 and l < 28 and s > 45:
        return "sandy clay loam"
    if 27 <= a < 40 and 20 < s <= 45:
        return "clay loam"
    if 27 <= a < 40 and s <= 20:
        return "silty clay loam"
    if a >= 35 and s > 45:
        return "sandy clay"
    if a >= 40 and l >= 40:
        return "silty clay"
    return "clay"


async def consultar_soilgrids(lat: float, lon: float) -> dict:
    """Consulta en vivo a SoilGrids. Devuelve {profundidad: {propiedad: valor sin escala}}."""
    clave = (round(lat, 3), round(lon, 3))
    if clave in _cache:
        return _cache[clave]
    params = [("lat", lat), ("lon", lon), ("value", "mean")]
    params += [("property", p) for p in PROPIEDADES]
    params += [("depth", d) for d in PROFUNDIDADES]
    try:
        async with httpx.AsyncClient(timeout=90) as cliente:
            r = await cliente.get(URL, params=params)
            r.raise_for_status()
            capas = r.json()["properties"]["layers"]
    except httpx.HTTPError as e:
        raise RuntimeError("SoilGrids did not respond (it is sometimes slow). Please try again in a moment.") from e
    datos = {}
    for capa in capas:
        factor = capa["unit_measure"]["d_factor"]
        for prof in capa["depths"]:
            valor = prof["values"].get("mean")
            datos.setdefault(prof["label"], {})[capa["name"]] = None if valor is None else valor / factor
    _cache[clave] = datos
    return datos


def guardar_tabla(tabla: dict) -> None:
    TABLA.parent.mkdir(parents=True, exist_ok=True)
    TABLA.write_text(
        json.dumps(
            {
                "fuente": "SoilGrids v2.0 (ISRIC), 250 m. Valores ya sin escala: pH, % (clay/sand/silt), g/kg (soc).",
                "actualizado": date.today().isoformat(),
                "puntos": tabla,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )


async def propiedades(lat: float, lon: float, municipio: str | None = None) -> dict:
    """Lee de la tabla; si el punto no está, consulta SoilGrids una vez y lo agrega a la tabla
    (así la tabla se llena sola conforme se consultan municipios)."""
    clave = clave_punto(lat, lon)
    guardado = _leer_tabla().get(clave)
    if guardado:
        datos, origen = guardado["datos"], "tabla"
    else:
        datos, origen = await consultar_soilgrids(lat, lon), "en vivo"
        if any(v.get("phh2o") is not None for v in datos.values()):  # no se guardan puntos sin dato
            origen = "en vivo (se guardó en la tabla)"
            async with _bloqueo:
                tabla = _leer_tabla()
                tabla[clave] = {"municipio": municipio, "lat": lat, "lon": lon, "datos": datos}
                guardar_tabla(tabla)
    capas = []
    for prof in PROFUNDIDADES:
        d = datos.get(prof, {})
        arcilla, arena, limo = d.get("clay"), d.get("sand"), d.get("silt")
        soc = d.get("soc")  # g/kg
        capas.append({
            "profundidad": prof,
            "ph": d.get("phh2o"),
            "arcilla_pct": arcilla,
            "arena_pct": arena,
            "limo_pct": limo,
            "textura": textura_usda(arena, limo, arcilla) if None not in (arcilla, arena, limo) else None,
            "carbono_organico_g_kg": soc,
            # Materia orgánica ESTIMADA = carbono orgánico × 1.724 (factor de Van Bemmelen), como indica
            # la NOM-021-SEMARNAT-2000. Factor empírico: en algunos suelos el real se acerca a 2.0 (Pribyl, 2010).
            "materia_organica_estimada_pct": round(soc * FACTOR_VAN_BEMMELEN / 10, 2) if soc is not None else None,
        })
    sin_datos = all(c["ph"] is None for c in capas)
    return {
        "capas": capas,
        "sin_datos": sin_datos,
        "aviso": "SoilGrids has no data here (probably urban area or water)." if sin_datos else None,
        "metodo_materia_organica": "Estimated: organic carbon × 1.724 (Van Bemmelen factor, NOM-021-SEMARNAT-2000)",
        "fuente": "SoilGrids (ISRIC), 250 m",
        "origen": origen,  # "tabla" = archivo pre-consultado; "en vivo" = consulta directa a SoilGrids
    }
