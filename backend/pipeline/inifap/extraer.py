"""Separa las Agendas Técnicas Agrícolas 2026 del INIFAP (PDF) en cultivos y secciones.

Plantilla 2026 (igual en los 31 estados):
- Índice general con páginas: "Maíz (Zea mays L.) ........ 129". Las fichas están entre
  "Paquetes tecnológicos" y "Bibliografía"/"Comité editorial"/"Agradecimientos".
- Cada ficha: título, nombre científico, autores, "Tipo de cultivo: ...",
  "Régimen hídrico: ...", y secciones de nombre casi fijo (Introducción, Región
  agroecológica, Siembra, Riego, Fertilización, Principales plagas y su control,
  Principales enfermedades y su control, Principal maleza y su control, Variedades o
  Híbridos, Cosecha).
- Al final, uno o más "Cuadro N. Costo beneficio ... de riego/temporal" (Agrocostos FIRA)
  con costo total, rendimiento, precio, ingreso neto y relación beneficio-costo. Esos
  números se extraen con reglas; el texto se resume aparte.
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pypdf

BACKEND_DIR = Path(__file__).resolve().parents[2]
AGENDAS_DIR = BACKEND_DIR / "data" / "inifap" / "agendas"
EXTRAIDO_DIR = BACKEND_DIR / "data" / "inifap" / "extraido"

# Nombre de archivo (ver data/inifap/README.md) -> clave INEGI del estado.
# Ciudad de México (09) no tiene agenda: la API usa la del Estado de México (15).
ESTADOS = {
    "aguascalientes": "01", "baja_california": "02", "baja_california_sur": "03", "campeche": "04",
    "coahuila": "05", "colima": "06", "chiapas": "07", "chihuahua": "08",
    "durango": "10", "guanajuato": "11", "guerrero": "12", "hidalgo": "13", "jalisco": "14",
    "mexico": "15", "michoacan": "16", "morelos": "17", "nayarit": "18", "nuevo_leon": "19",
    "oaxaca": "20", "puebla": "21", "queretaro": "22", "quintana_roo": "23", "san_luis_potosi": "24",
    "sinaloa": "25", "sonora": "26", "tabasco": "27", "tamaulipas": "28", "tlaxcala": "29",
    "veracruz": "30", "yucatan": "31", "zacatecas": "32",
}

SECCIONES = {
    "introduccion": r"introduccion",
    "region": r"region agroecologica|requerimientos? (agro)?climaticos?|clima y suelos?",
    "manejo": r"manejo agronomico",
    "terreno": r"(seleccion (y preparacion )?del terreno|preparacion del (terreno|suelo))",
    "fecha_siembra": r"(epoca|fecha|fechas|periodos?) de (siembra|plantacion)",
    "densidad": r"densidad de (siembra|poblacion|plantacion)|cantidad de semilla",
    "siembra": r"siembra|metodos? de siembra|plantacion|establecimiento( del cultivo)?",
    "riego": r"riegos?|manejo del (agua|riego)|calendario de riegos",
    "fertilizacion": r"fertilizacion|nutricion|fertilizacion y nutricion",
    "plagas": r"(principales )?(insectos )?plagas?( y su control| insectiles)?|control de (insectos )?plagas"
              r"|manejo (integrado )?de plagas( y enfermedades)?",
    "enfermedades": r"(principales )?enfermedades( y su control)?|control de enfermedades",
    "malezas": r"(principal(es)? )?(malezas?|arvenses)( y su control)?|control de (la )?(malezas?|arvenses)"
               r"|manejo (integrado )?de (malezas?|arvenses)",
    "variedades": r"variedades( o hibridos| e hibridos| recomendadas)?|hibridos( y variedades)?"
                  r"|variedades y/o hibridos|portainjertos? y variedades|variedades inifap",
    "labores": r"podas?|labores (culturales|de cultivo)|aporque",
    "cosecha": r"cosecha( y poscosecha)?|rendimiento esperado",
}
PATRONES = {k: re.compile(rf"^({v})$") for k, v in SECCIONES.items()}
SALIDA_DE_COSTOS = {"introduccion", "region", "variedades"}
FIN_FICHAS = re.compile(r"^(bibliografia|comite editorial|agradecimientos|directorio|literatura citada)")
LIDER = re.compile(r"(?:[.…]\s*){3,}")
NUM = r"(-?\$?\s?[\d,]+(?:\.\d+)?)"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _num(s: str):
    try:
        return float(s.replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


PRELIMINARES = re.compile(r"^(presentacion|abreviaturas|generalidades|ubicacion|orografia|hidrografia|clima"
                          r"|extension|uso de suelo|contenido|indice|paquetes tecnologicos|temperatura|precipitacion|suelos?$)")


def _indice(textos: list[str]) -> list[tuple[str, int]]:
    """Entradas (nombre, página impresa) de los paquetes tecnológicos.

    El índice puede ocupar varias hojas (Campeche) y no siempre tiene la línea
    "Paquetes tecnológicos" (Estado de México): en ese caso se toman las entradas
    que no son preliminares (presentación, generalidades, clima...).
    """
    for i, t in enumerate(textos[:10]):
        if "ndice" not in t[:300]:
            continue
        plano = re.sub(r"\s+", " ", " ".join(textos[i:i + 3]).replace("¡Error! Marcador no definido.", " 0 "))
        entradas = re.findall(r"([A-ZÁÉÍÓÚÑ0-9][^.…]*?(?:\([^)]*\))?[^.…]*?)\s*\.?\s*(?:[.…]\s*){3,}\s*(\d{1,3})", plano)
        entradas = [(re.sub(r"^\d+\.?\s+", "", n).strip(" ."), int(p)) for n, p in entradas]
        hay_marca = any(_norm(n).startswith("paquetes tecnologicos") for n, _ in entradas)
        out, dentro, ultima = [], not hay_marca, 0
        for nombre, pag in entradas:
            n = _norm(nombre)
            if n.startswith("paquetes tecnologicos"):
                dentro = True
                continue
            if FIN_FICHAS.match(n) and out:
                break
            if dentro and not PRELIMINARES.match(n) and pag > ultima:
                out.append((nombre, pag))
                ultima = pag
        if out:
            return out
    return []


def _desfase(textos: list[str]) -> int:
    """pdf_idx - página impresa (la página impresa es el primer número de cada hoja)."""
    difs = Counter()
    for i, t in enumerate(textos):
        m = re.match(r"\s*(\d{1,3})\s", t)
        if m:
            difs[i - int(m.group(1))] += 1
    return difs.most_common(1)[0][0] if difs else 0


def _costos(texto: str) -> list[dict]:
    """Cuadros 'Costo beneficio' (Agrocostos FIRA) de una ficha."""
    plano = re.sub(r"\s+", " ", texto)
    # Quitar unidades como "kg ha-1" o "t ha⁻¹": su "1" se leía como rendimiento.
    plano = re.sub(r"\b(ha|L|kg|t|pl)\s?(?:-\s?1|⁻¹)", r"\1", plano)
    partes = re.split(r"(?=Cuadro \d+\.? ?Costos?\W{0,3}(?:y |de )?(?:beneficio|producci))", plano, flags=re.I)
    cuadros = []
    for p in partes[1:]:
        titulo = re.match(r"(Cuadro \d+\.?[^$]{0,160}?)(?: Concepto|$)", p)
        titulo = titulo.group(1).strip() if titulo else p[:120]
        t = _norm(titulo)
        modalidad = "riego" if "riego" in t else "temporal" if "temporal" in t else None
        busca = lambda pat: (lambda m: _num(m.group(1)) if m else None)(re.search(pat, p, re.I))
        c = {
            "titulo": titulo,
            "modalidad": modalidad,
            "costo_total_ha": busca(rf"Costo total(?: de producci[oó]n)?\s*(?:\(\$[^)]*\))?\s*{NUM}"),
            "rendimiento": busca(rf"Rendimiento[^0-9$]{{0,40}}{NUM}"),
            "precio": busca(rf"Precio (?:probable|medio rural|de venta|promedio)[^0-9$]{{0,30}}{NUM}"),
            "ingreso_bruto": busca(rf"Ingreso bruto[^0-9$-]{{0,20}}{NUM}"),
            "ingreso_neto": busca(rf"Ingreso neto[^0-9$-]{{0,20}}{NUM}"),
            "relacion_bc": busca(rf"Relaci[oó]n beneficio[\s/-]*costo\s*(?:\(?B/C\)?)?\s*:?\s*{NUM}")
                            or busca(rf"B/C\s*:?\s*{NUM}"),
        }
        c["texto"] = p[:8000]  # tabla cruda: los valores parseados son solo una pista
        if any(v is not None for k, v in c.items() if k not in ("titulo", "modalidad", "texto")):
            cuadros.append(c)
    return cuadros


def segmentar(ruta: Path) -> dict:
    textos = [(p.extract_text() or "") for p in pypdf.PdfReader(ruta).pages]
    indice = _indice(textos)
    desfase = _desfase(textos)
    fichas, sin_reconocer = [], Counter()
    for k, (nombre, pag) in enumerate(indice):
        ini = pag + desfase
        fin = (indice[k + 1][1] + desfase - 1) if k + 1 < len(indice) else None
        if fin is None:  # última ficha: hasta la bibliografía o el final
            fin = len(textos) - 1
            for j in range(ini + 1, len(textos)):
                primera = next((l for l in textos[j].split("\n")[1:4] if l.strip()), "")
                if FIN_FICHAS.match(_norm(primera)):
                    fin = j - 1
                    break
        cuerpo = "\n".join(textos[ini:fin + 1])
        cientifico = re.search(r"\(([A-Z][a-z]+ [a-z×x.\- ]+[^)]{0,40})\)", nombre + "\n" + cuerpo[:600])
        # En PDFs sin saltos de línea (Michoacán) los campos vienen pegados: se corta
        # en el siguiente campo o encabezado y a lo más a 40 caracteres.
        corte = r"(?=\s*(?:R[ée]gimen|Tipo de cultivo|Introducci|\n|$))"
        tipo = re.search(rf"Tipo de cultivo:\s*(.{{1,40}}?){corte}", cuerpo)
        regimen = re.search(rf"R[ée]gimen (?:h[íi]drico|de riego):\s*(.{{1,40}}?){corte}", cuerpo)

        secciones, actual = {}, "encabezado"
        for l in cuerpo.split("\n"):
            l = l.strip()
            if not l or re.fullmatch(r"\d{1,3}", l):
                continue
            n = _norm(l)
            if re.match(r"cuadro \d+\.? ?costos?\W{0,3}(y |de )?(beneficio|producci)", n):
                actual = "costos"
            elif actual == "costos" and n.startswith("fuente:"):
                # Fin del cuadro: lo que sigue (otra modalidad o región) vuelve a ser texto.
                secciones.setdefault("costos", []).append(l)
                actual = "manejo"
                continue
            else:
                nueva = next((s for s, p in PATRONES.items() if p.match(n)), None)
                # Dentro de un cuadro de costos hay filas de categoría ("Siembra", "Cosecha",
                # "Riego"...) que coinciden con nombres de sección: ahí solo se sale con
                # encabezados que nunca son una fila de costos.
                if nueva and (actual != "costos" or nueva in SALIDA_DE_COSTOS):
                    actual = nueva
                    continue
                if (actual != "costos" and len(l) < 50 and l[0].isupper()
                        and not l.endswith((".", ",", ";", ":"))
                        and not re.search(r"\d", l) and len(l.split()) <= 6):
                    sin_reconocer[l] += 1
            secciones.setdefault(actual, []).append(l)
        secciones = {s: re.sub(r"\s+", " ", " ".join(v)).replace("- ", "") for s, v in secciones.items()}
        texto_costos = secciones.pop("costos", "")
        encabezado = secciones.pop("encabezado", "")
        # "manejo" se conserva: en muchas fichas siembra, riego y fertilización van ahí sin encabezado propio.
        if len(secciones) < 4:
            # PDF sin saltos de línea (Michoacán): los encabezados quedan pegados al
            # texto. Se guarda el texto completo para el resumen.
            secciones = {"texto_completo": re.sub(r"\s+", " ", encabezado + " " + " ".join(secciones.values()))}
            if not texto_costos:
                m = re.search(r"Cuadro \d+\.? ?Costos?\W{0,3}(?:y |de )?(?:beneficio|producci)", cuerpo, re.I)
                texto_costos = cuerpo[m.start():] if m else ""

        fichas.append({
            "ficha": re.sub(r"\s*\(.*", "", nombre).strip(),
            "cientifico": cientifico.group(1).strip() if cientifico else None,
            "tipo_cultivo": tipo.group(1).strip(" .").lower() if tipo else None,
            "regimen_hidrico": re.sub(r"\s*/\s*", "/", regimen.group(1).strip(" .").lower()) if regimen else None,
            "paginas": [ini + 1, fin + 1],
            "secciones": secciones,
            "costos": _costos(texto_costos),
        })
    return {
        "archivo": ruta.name,
        "edicion": 2026,
        "fichas": fichas,
        "avisos": {
            "n_fichas_indice": len(indice),
            "fichas_sin_secciones": [f["ficha"] for f in fichas if "texto_completo" in f["secciones"]],
            "fichas_sin_costos": [f["ficha"] for f in fichas if not f["costos"]],
            "posibles_encabezados_no_reconocidos": [k for k, v in sin_reconocer.most_common(25) if v >= 2],
        },
    }


def extraer_todo():
    pdfs = sorted(AGENDAS_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No hay PDF en {AGENDAS_DIR}. Ver data/inifap/README.md")
        return
    EXTRAIDO_DIR.mkdir(parents=True, exist_ok=True)
    for ruta in pdfs:
        cve = ESTADOS.get(ruta.stem)
        if cve is None:
            print(f"  {ruta.name}: nombre no reconocido, renómbralo como en el README")
            continue
        datos = segmentar(ruta)
        datos["cve_ent"] = cve
        with open(EXTRAIDO_DIR / f"{ruta.stem}.json", "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        a = datos["avisos"]
        print(f"  {ruta.stem}: {len(datos['fichas'])} fichas; sin secciones {len(a['fichas_sin_secciones'])}, "
              f"sin costos {len(a['fichas_sin_costos'])}")
