"""Paso de traducción al inglés de la pipeline de Cultivos.

Casi todo el texto que genera la pipeline sale de plantillas que ya están en inglés. Lo
único que llega en español desde las fuentes son los nombres de cultivo de SIAP, los tipos
y las unidades: se traducen con glosario_en.json. Si SIAP agrega un cultivo que no está en
el glosario, se intenta DeepL (variable de entorno DEEPL_API_KEY) y el resultado se guarda en
traducciones_cache.json para no volver a pedirlo; sin llave, el nombre queda en español y se
reporta al final de la corrida para agregarlo al glosario.
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

DIR = Path(__file__).resolve().parent
GLOSARIO_JSON = DIR / "glosario_en.json"
CACHE_JSON = DIR / "traducciones_cache.json"

with open(GLOSARIO_JSON, encoding="utf-8") as _f:
    _GLOSARIO = json.load(_f)
_cache: dict[str, str] = json.loads(CACHE_JSON.read_text(encoding="utf-8")) if CACHE_JSON.exists() else {}
_faltantes: set[str] = set()


def _deepl(texto: str) -> str | None:
    llave = os.environ.get("DEEPL_API_KEY")
    if not llave:
        return None
    host = "api-free.deepl.com" if llave.endswith(":fx") else "api.deepl.com"
    datos = urllib.parse.urlencode({"text": texto, "source_lang": "ES", "target_lang": "EN-US"}).encode()
    req = urllib.request.Request(f"https://{host}/v2/translate", data=datos,
                                 headers={"Authorization": f"DeepL-Auth-Key {llave}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["translations"][0]["text"]
    except Exception as e:  # noqa: BLE001 - sin red o sin cuota: se queda en español
        print(f"  DeepL falló para {texto!r}: {e}")
        return None


def _traducir(texto: str, seccion: str) -> str:
    if not texto:
        return texto
    if texto in _GLOSARIO[seccion]:
        return _GLOSARIO[seccion][texto]
    if texto in _cache:
        return _cache[texto]
    en = _deepl(texto)
    if en:
        _cache[texto] = en
        return en
    _faltantes.add(f"{seccion}: {texto}")
    return texto


def cultivo(nombre: str) -> str:
    return _traducir(nombre, "cultivos")


def unidad(nombre: str) -> str:
    return _traducir(nombre, "unidades")


def tipo(nombre: str | None) -> str | None:
    """Los tipos pueden venir ya en inglés (curado.json traducido) o en español."""
    if nombre is None or nombre in _GLOSARIO["tipos"].values():
        return nombre
    return _traducir(nombre, "tipos")


def cerrar():
    """Guarda la caché de DeepL y reporta lo que quedó sin traducir."""
    if _cache:
        CACHE_JSON.write_text(json.dumps(_cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if _faltantes:
        print(f"  AVISO: {len(_faltantes)} textos quedaron en español; agrégalos a glosario_en.json:")
        for t in sorted(_faltantes):
            print(f"    - {t}")
