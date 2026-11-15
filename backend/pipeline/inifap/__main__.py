"""Extrae el texto de las Agendas Técnicas del INIFAP por cultivo y sección.

Uso (desde backend/):  python -m pipeline.inifap
Lee data/inifap/agendas/*.pdf y escribe data/inifap/extraido/<estado>.json.
"""

from .extraer import extraer_todo

if __name__ == "__main__":
    print("Extrayendo agendas INIFAP:")
    extraer_todo()
