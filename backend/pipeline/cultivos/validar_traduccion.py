"""Compara un JSON en español con su traducción al inglés.

Uso (desde backend/):  python -m pipeline.cultivos.validar_traduccion ORIGINAL.json TRADUCIDO.json

Comprueba que la traducción conserve la estructura (mismas llaves, mismas longitudes de
listas), los números y los campos de código sin traducir, y avisa de textos que parecen
seguir en español. Sale con código 1 si hay errores de estructura.
"""

import json
import re
import sys

# Campos cuyo valor NO se traduce (códigos, ids, números, nombres científicos).
SIN_TRADUCIR = {"cve_ent", "paginas", "cultivo_ids", "ciclo", "meses", "revisado", "edicion",
                "cientifico", "eppocode", "unidad_rendimiento_codigo"}
# Valores enum con traducción fija.
ENUMS = {
    "modalidad": {"riego": "irrigated", "temporal": "rainfed"},
    "tipo_cultivo": {"anual": "annual", "perenne": "perennial", "anual/perenne": "annual/perennial"},
}
ESPANOL = re.compile(r"(?i)\b(de la|del|los|las|para|siembra|semilla|cosecha|riego|temporal|plagas?|"
                     r"variedad(es)?|cultivo|suelo|lluvias?|meses|días|hasta|desde|también|según|"
                     r"fertiliza\w*|maleza|enfermedad(es)?|aplicar|sembrar|cuando|con|sin|por)\b|[ñ¿¡]")


def comparar(es, en, ruta, errores, avisos):
    if isinstance(es, dict):
        if not isinstance(en, dict) or set(es) != set(en):
            errores.append(f"{ruta}: llaves distintas {sorted(set(es) ^ set(en if isinstance(en, dict) else {}))}")
            return
        for k in es:
            sub = f"{ruta}.{k}"
            if k in SIN_TRADUCIR:
                if es[k] != en[k]:
                    errores.append(f"{sub}: no debía cambiar ({es[k]!r} -> {en[k]!r})")
            elif k in ENUMS and isinstance(es[k], str):
                esperado = ENUMS[k].get(es[k], es[k])
                if en[k] != esperado:
                    errores.append(f"{sub}: se esperaba {esperado!r}, hay {en[k]!r}")
            else:
                comparar(es[k], en[k], sub, errores, avisos)
    elif isinstance(es, list):
        if not isinstance(en, list) or len(es) != len(en):
            errores.append(f"{ruta}: longitud distinta ({len(es)} vs {len(en) if isinstance(en, list) else '?'})")
            return
        for i, (a, b) in enumerate(zip(es, en)):
            comparar(a, b, f"{ruta}[{i}]", errores, avisos)
    elif isinstance(es, (int, float)) and not isinstance(es, bool):
        if es != en:
            errores.append(f"{ruta}: número cambió ({es} -> {en})")
    elif isinstance(es, str):
        if not isinstance(en, str):
            errores.append(f"{ruta}: tipo cambió")
        elif len(es) > 25 and ESPANOL.search(en):
            avisos.append(f"{ruta}: ¿sigue en español? {en[:90]!r}")
    elif es != en:
        errores.append(f"{ruta}: valor cambió ({es!r} -> {en!r})")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    es = json.load(open(sys.argv[1], encoding="utf-8"))
    en = json.load(open(sys.argv[2], encoding="utf-8"))
    errores, avisos = [], []
    comparar(es, en, "$", errores, avisos)
    for e in errores:
        print("ERROR", e)
    for a in avisos[:40]:
        print("AVISO", a)
    print(f"{len(errores)} errores, {len(avisos)} avisos")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
