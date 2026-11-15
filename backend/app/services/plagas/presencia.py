"""¿Hay registros georreferenciados de la plaga cerca? GBIF e iNaturalist, en un radio de 100 km.

Es una pista, no una detección: un registro cercano sube el riesgo; no haberlo no descarta nada
(los registros dependen de que alguien los suba). Se guarda en disco 7 días por especie y zona
(coordenadas redondeadas a medio grado, unos 50 km).
"""

import asyncio
import math

import httpx

from app.services.plagas import cache

GBIF = "https://api.gbif.org/v1/occurrence/search"
INAT = "https://api.inaturalist.org/v1/observations"
RADIO_KM = 100.0
DIAS_CACHE = 7


def especie(nombre_eppo: str) -> str:
    """Género y especie ("Candidatus" y los autores se quitan): lo que entienden GBIF e iNaturalist."""
    partes = nombre_eppo.strip().replace("'", "").split()
    if len(partes) >= 3 and partes[0].lower() == "candidatus":
        return f"{partes[1]} {partes[2]}"
    return " ".join(partes[:2]) if len(partes) >= 2 else nombre_eppo.strip()


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat, d_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return round(6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


async def _gbif(cliente: httpx.AsyncClient, nombre: str, lat: float, lon: float) -> list[dict] | None:
    d_lat = RADIO_KM / 111.0
    d_lon = RADIO_KM / (111.0 * max(0.1, math.cos(math.radians(lat))))
    parametros = {
        "scientificName": nombre, "hasCoordinate": "true", "limit": 30,
        "decimalLatitude": f"{lat - d_lat:.4f},{lat + d_lat:.4f}",
        "decimalLongitude": f"{lon - d_lon:.4f},{lon + d_lon:.4f}",
    }
    try:
        r = await cliente.get(GBIF, params=parametros)
        if r.status_code != 200:
            return None
        hallazgos = []
        for reg in r.json().get("results", []):
            r_lat, r_lon = reg.get("decimalLatitude"), reg.get("decimalLongitude")
            if r_lat is None or r_lon is None:
                continue
            dist = distancia_km(lat, lon, r_lat, r_lon)
            if dist <= RADIO_KM:
                hallazgos.append({"fuente": "GBIF", "distanciaKm": dist,
                                  "lugar": reg.get("stateProvince") or reg.get("locality") or "Nearby region",
                                  "fecha": str(reg.get("eventDate") or reg.get("year") or "Historical")[:10]})
        return hallazgos
    except (httpx.HTTPError, ValueError):
        return None


async def _inat(cliente: httpx.AsyncClient, nombre: str, lat: float, lon: float) -> list[dict] | None:
    try:
        r = await cliente.get(INAT, params={"taxon_name": nombre, "lat": lat, "lng": lon, "radius": RADIO_KM, "per_page": 20})
        if r.status_code != 200:
            return None
        hallazgos = []
        for obs in r.json().get("results", []):
            coords = (obs.get("geojson") or {}).get("coordinates")
            if not coords or len(coords) != 2:
                continue
            dist = distancia_km(lat, lon, float(coords[1]), float(coords[0]))
            if dist <= RADIO_KM:
                hallazgos.append({"fuente": "iNaturalist", "distanciaKm": dist,
                                  "lugar": obs.get("place_guess") or "Nearby region",
                                  "fecha": str(obs.get("observed_on") or "Recent")[:10]})
        return hallazgos
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def resumir(hallazgos: list[dict]) -> dict:
    hallazgos = sorted(hallazgos, key=lambda h: h["distanciaKm"])
    cercano = hallazgos[0] if hallazgos else None
    return {
        "detectada": bool(hallazgos),
        "radioKm": RADIO_KM,
        "registros": len(hallazgos),
        "masCercanoKm": cercano["distanciaKm"] if cercano else None,
        "lugar": cercano["lugar"] if cercano else None,
        "ultimoRegistro": cercano["fecha"] if cercano else None,
    }


async def cerca(cliente: httpx.AsyncClient, nombre_cientifico: str, lat: float, lon: float) -> dict:
    """Resumen de registros de la plaga a menos de 100 km (con caché de 7 días).

    Si una fuente no responde se usa lo de la otra, pero el resultado no se guarda."""
    nombre = especie(nombre_cientifico)
    llave = f"{nombre}_{round(lat * 2) / 2}_{round(lon * 2) / 2}"
    guardado = cache.leer("presencia", llave, DIAS_CACHE)
    if guardado is not None:
        return guardado
    gbif, inat = await asyncio.gather(_gbif(cliente, nombre, lat, lon), _inat(cliente, nombre, lat, lon))
    resumen = resumir((gbif or []) + (inat or []))
    if gbif is not None and inat is not None:  # si una fuente falló no se guarda: "sin registros" sería falso
        cache.escribir("presencia", llave, resumen)
    return resumen
