"""Noticias: avisos propios (calculados con nuestros datos) y titulares de feeds RSS externos.

Las noticias propias salen del clima, las alertas y el plan del usuario; siempre están disponibles.
Las externas vienen de feeds públicos en inglés (CIMMYT, el centro internacional de maíz y trigo, y
NASA Earth Observatory). Si un feed falla, se omite y el resto de la pantalla sigue funcionando.
Todo el texto que ve el usuario va en inglés.
"""

import asyncio
import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

SEGUNDOS_CACHE = 1800  # 30 minutos
SEGUNDOS_CACHE_ERROR = 300
POR_FEED = 8
DIAS_COSECHA_CERCANA = 45

# categoria: "farm" (tu campo), "weather" (clima) o "research" (noticias externas)
FEEDS = [
    {"fuente": "CIMMYT", "url": "https://www.cimmyt.org/feed/"},
    {"fuente": "NASA Earth Observatory", "url": "https://earthobservatory.nasa.gov/feeds/earth-observatory.rss"},
]

_cache: dict[str, tuple[float, list[dict] | None]] = {}


def _sin_html(texto: str | None, maximo: int = 220) -> str:
    limpio = html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))
    limpio = " ".join(limpio.split()).split(" What to read next")[0]  # resto que agrega el feed de CIMMYT
    limpio = limpio.split(" The post ")[0]  # y el de NASA ("The post ... appeared first on ...")
    return limpio if len(limpio) <= maximo else limpio[: maximo - 1].rstrip() + "…"


def _enlace_seguro(url: str | None) -> str | None:
    """Solo se aceptan enlaces http(s): nada de javascript: ni otros esquemas."""
    return url if url and urlparse(url).scheme in ("http", "https") else None


def parsear_rss(xml: str, fuente: str) -> list[dict]:
    """Convierte un RSS 2.0 en noticias. Ignora entradas sin título o sin enlace válido."""
    items = []
    # El feed de NASA trae atributos pegados en la primera etiqueta (..."xmlns:media=...): se separan
    xml = re.sub(r'"(xmlns:)', r'" \1', xml)
    for nodo in ET.fromstring(xml).iter("item"):
        titulo = _sin_html(nodo.findtext("title"), 160)
        enlace = _enlace_seguro((nodo.findtext("link") or "").strip())
        if not titulo or not enlace:
            continue
        try:
            fecha = parsedate_to_datetime(nodo.findtext("pubDate") or "").date().isoformat()
        except (TypeError, ValueError):
            fecha = None
        items.append({
            "id": f"{fuente}-{enlace}",
            "categoria": "research",
            "titulo": titulo,
            "resumen": _sin_html(nodo.findtext("description")),
            "fuente": fuente,
            "fecha": fecha,
            "enlace": enlace,
            "destino": None,
        })
    items.sort(key=lambda i: i["fecha"] or "", reverse=True)
    return items[:POR_FEED]


async def _leer_feed(cliente: httpx.AsyncClient, feed: dict) -> list[dict] | None:
    llave = feed["url"]
    guardado = _cache.get(llave)
    if guardado and time.monotonic() - guardado[0] < (SEGUNDOS_CACHE if guardado[1] is not None else SEGUNDOS_CACHE_ERROR):
        return guardado[1]
    try:
        r = await cliente.get(feed["url"], headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        r.raise_for_status()
        items = parsear_rss(r.text, feed["fuente"])
    except (httpx.HTTPError, ET.ParseError):
        items = None
    _cache[llave] = (time.monotonic(), items)
    return items


async def externas() -> tuple[list[dict], bool]:
    """Titulares de los feeds. Devuelve (noticias, todos_respondieron)."""
    async with httpx.AsyncClient(timeout=10) as cliente:
        resultados = await asyncio.gather(*(_leer_feed(cliente, f) for f in FEEDS))
    noticias = [n for r in resultados if r for n in r]
    noticias.sort(key=lambda i: i["fecha"] or "", reverse=True)
    return noticias, all(r is not None for r in resultados)


def _atraso(dias: int) -> str:
    return "1 day late" if dias == 1 else f"{dias} days late"


UMBRAL_PRECIO_PCT = 5  # cambio del precio al consumidor en 30 días a partir del cual es noticia


def _noticia_de_precio(t: dict, ahora: str) -> dict | None:
    """Noticia de un producto cuyo precio al consumidor (Profeco) cambió bastante. `t` es lo que devuelve `mercado.tendencia`.

    No se crea si el último dato real está desactualizado: "subió este mes" sobre datos de hace meses no es noticia.
    """
    cambio = t.get("cambio30dPct")
    if t.get("desactualizado") or cambio is None or abs(cambio) < UMBRAL_PRECIO_PCT:
        return None
    proyectado = t.get("proyeccion30dPct")
    siguiente = f" Projected change over the next 30 days: {proyectado:+.0f}%." if proyectado is not None else ""
    return {
        "id": f"precio-{t['producto']}",
        "categoria": "farm",
        "titulo": f"{t['nombre'].title()} {'up' if cambio > 0 else 'down'} {abs(cambio):.0f}% in {t['estado'].title()} over 30 days",
        "resumen": (
            f"Latest retail price: {t['precio']:.1f} {t['unidad']} (as of {t['fecha']}).{siguiente} "
            "These are consumer prices from Profeco, not farm-gate prices."
        ),
        "fuente": "Profeco",
        "fecha": ahora,
        "enlace": None,
        "destino": "mercado",
    }


def propias(
    alertas: list[dict], activos: list[dict], nasa: dict | None, lugar: str, hoy: date, vencidas: dict | None = None,
    precios: list[dict] | None = None,
) -> list[dict]:
    """Noticias calculadas con los datos del usuario: alertas, tareas vencidas, cosechas cercanas, precios y lluvia reciente.

    `vencidas` es lo que devuelve `tareas.vencidas` (total y las más atrasadas) y `precios` las tendencias de
    `mercado.tendencia` de los cultivos en curso.
    """
    ahora = hoy.isoformat()
    items = []

    for a in alertas:
        cultivos = f" Your crops: {', '.join(a['cultivos'])}." if a["cultivos"] else ""
        items.append({
            "id": f"alerta-{a['id']}",
            "categoria": "farm" if a["tipo"] == "plaga" else "weather",
            "titulo": a["titulo"],
            "resumen": a["detalle"] + cultivos,
            "fuente": "CroPro alerts",
            "fecha": ahora,
            "enlace": None,
            "destino": "principal",
        })

    if vencidas and vencidas["total"]:
        n, peor = vencidas["total"], vencidas["tareas"][0]
        items.append({
            "id": "tareas-vencidas",
            "categoria": "farm",
            "titulo": f"{n} overdue task{'' if n == 1 else 's'}",
            "resumen": (
                f"The oldest: {peor['titulo']} for {peor['cultivo']} · {peor['parcela']} ({_atraso(peor['dias_retraso'])}). "
                "Mark tasks as done or move their dates in the Planner."
            ),
            "fuente": "Your plan",
            "fecha": ahora,
            "enlace": None,
            "destino": "planificador",
        })

    cercanas = sorted(
        (a for a in activos if a["dias_totales"] - a["dia"] <= DIAS_COSECHA_CERCANA),
        key=lambda a: a["dias_totales"] - a["dia"],
    )
    for a in cercanas:
        faltan = a["dias_totales"] - a["dia"]
        cuando = "tomorrow" if faltan == 1 else "today" if faltan <= 0 else f"in {faltan} days"
        items.append({
            "id": f"cosecha-{a['id']}",
            "categoria": "farm",
            "titulo": f"{a['cultivo']['nombre']} harvest {cuando}",
            "resumen": f"{a['parcela']['nombre']} · {a['hectareas']} ha. Plan the harvest and what to plant next.",
            "fuente": "Your plan",
            "fecha": ahora,
            "enlace": None,
            "destino": "planificador",
        })

    for t in precios or []:
        noticia = _noticia_de_precio(t, ahora)
        if noticia:
            items.append(noticia)

    if nasa and nasa.get("dias") and nasa.get("lluviaMm") is not None:
        items.append({
            "id": "nasa-lluvia",
            "categoria": "weather",
            "titulo": f"{nasa['lluviaMm']} mm of rain in the last 30 days at {lugar}",
            "resumen": (
                f"It rained on {nasa['diasConLluvia']} days. Average temperature {nasa['tempMedia']} °C"
                + (f", root-zone moisture {nasa['humedadRaizPct']}%" if nasa.get("humedadRaizPct") is not None else "")
                + ". Satellite data from NASA POWER."
            ),
            "fuente": "NASA POWER",
            "fecha": ahora,
            "enlace": None,
            "destino": "principal",
        })
    return items
