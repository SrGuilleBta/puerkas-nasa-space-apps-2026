"""Exporta un plan a PDF: resumen, una línea de tiempo con las parcelas y la tabla de siembras de cada una.

Usa fpdf2 con las fuentes estándar de PDF (Helvetica), que solo cubren Latin-1: los acentos y la ñ salen
bien y cualquier otro carácter (p. ej. un nombre escrito en otro alfabeto) se cambia por "?" en vez de
hacer fallar la descarga. Todo el texto del documento va en inglés, como la interfaz.
"""

import re
from datetime import date

from fpdf import FPDF
from fpdf.fonts import FontFace

from app.db import clave
from app.services import planificador as plan_servicio
from app.services import tareas
from app.services.planificador import obtener_plan

VERDE = (10, 122, 75)
TINTA = (18, 48, 74)
SUAVE = (93, 117, 135)
FONDO = (241, 246, 244)
BORDE = (214, 224, 220)
# Los mismos colores por cultivo que el calendario de la app (utils/colores.js): verano, primavera,
# otoño, ámbar, invierno y violeta.
PALETA = [(25, 195, 230), (34, 224, 122), (242, 125, 125), (242, 180, 65), (107, 138, 176), (155, 140, 240)]
MESES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

ANCHO_ETIQUETA = 40  # mm que ocupa el nombre de la parcela a la izquierda de la línea de tiempo
ALTO_FILA = 9
MARGEN_INFERIOR = 15


def _t(texto) -> str:
    """Texto seguro para las fuentes estándar del PDF (Latin-1)."""
    return str(texto).encode("latin-1", "replace").decode("latin-1")


def _fecha(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{MESES[d.month - 1]} {d.day}, {d.year}"


def _pesos(n) -> str:
    return "-" if n is None else f"${n:,.0f}"


def _siguiente_mes(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


class _Documento(FPDF):
    def __init__(self, titulo: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.titulo = titulo
        self.set_auto_page_break(True, MARGEN_INFERIOR)
        self.set_margins(10, 12, 10)
        self.alias_nb_pages()
        self.set_title(_t(titulo))
        self.set_creator("CroPro")

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SUAVE)
        self.cell(0, 5, _t(f"CroPro - {self.titulo}") + f" - Page {self.page_no()} of {{nb}}", align="C")


def _recortar(pdf: FPDF, texto: str, ancho: float) -> str:
    """Acorta el texto, con '..' al final, hasta que quepa en `ancho` mm con la fuente actual."""
    texto = _t(texto)
    if pdf.get_string_width(texto) <= ancho:
        return texto
    while len(texto) > 1 and pdf.get_string_width(texto + "..") > ancho:
        texto = texto[:-1]
    return texto + ".." if pdf.get_string_width(texto + "..") <= ancho else ""


def _resumen(pdf: _Documento, plan: dict, resumen: dict, abiertas: dict) -> None:
    """Cifras del plan en una fila de recuadros y, debajo, la economía estimada si hay datos."""
    cajas = [
        ("Plots", str(len(plan["parcelas"]))),
        ("Hectares", f"{resumen['hectareas_totales']:g}"),
        ("Plantings", str(resumen["total_siembras"])),
        ("Distinct crops", str(resumen["cultivos_distintos"])),
        ("Land in use today", f"{resumen['uso_suelo']}%"),
    ]
    ancho = (pdf.epw - 4 * 3) / 5
    y = pdf.get_y()
    for i, (etiqueta, valor) in enumerate(cajas):
        x = pdf.l_margin + i * (ancho + 3)
        pdf.set_fill_color(*FONDO)
        pdf.set_draw_color(*BORDE)
        pdf.rect(x, y, ancho, 16, style="DF", round_corners=True, corner_radius=2)
        pdf.set_xy(x, y + 2)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*SUAVE)
        pdf.cell(ancho, 4, _t(etiqueta.upper()), align="C")
        pdf.set_xy(x, y + 7)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*TINTA)
        pdf.cell(ancho, 7, _t(valor), align="C")
    pdf.set_y(y + 20)

    lineas = []
    proxima = resumen["proxima_cosecha"]
    if proxima:
        lineas.append(f"Next harvest: {proxima['cultivo']} - {proxima['parcela']} - {_fecha(proxima['fecha'])} (in {proxima['dias_restantes']} days)")
    if resumen["ganancia_estimada"] is not None or resumen["ingreso_estimado"] is not None or resumen["inversion_estimada"] is not None:
        lineas.append(
            f"Estimated investment {_pesos(resumen['inversion_estimada'])}  |  income {_pesos(resumen['ingreso_estimado'])}  |  "
            f"profit {_pesos(resumen['ganancia_estimada'])} (MXN; only plantings with enough data)"
        )
    if abiertas["tareas_pendientes"]:
        vencidas = abiertas["tareas_vencidas"]
        lineas.append(f"Open tasks: {abiertas['tareas_pendientes']}" + (f" ({vencidas} overdue)" if vencidas else ""))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TINTA)
    for linea in lineas:
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 5, _t(linea), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _linea_de_tiempo(pdf: _Documento, plan: dict) -> None:
    """Una fila por parcela con una barra por siembra, sobre los meses que cubre el plan."""
    pares = [(p, s) for p in plan["parcelas"] for s in p["siembras"]]
    if not pares:
        return
    primero = min(date.fromisoformat(s["fecha_siembra"]) for _, s in pares)
    ultimo = max(date.fromisoformat(s["fecha_cosecha"]) for _, s in pares)
    inicio = date(primero.year, primero.month, 1)
    fin = _siguiente_mes(ultimo)
    total_dias = (fin - inicio).days
    meses = []
    m = inicio
    while m < fin:
        meses.append(m)
        m = _siguiente_mes(m)
    paso = 1 if len(meses) <= 14 else 3 if len(meses) <= 40 else 6  # cada cuántos meses lleva etiqueta

    x0 = pdf.l_margin + ANCHO_ETIQUETA
    ancho = pdf.epw - ANCHO_ETIQUETA
    x_de = lambda d: x0 + ancho * (d - inicio).days / total_dias  # noqa: E731

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*VERDE)
    pdf.cell(0, 7, "Planting calendar", new_x="LMARGIN", new_y="NEXT")

    def encabezado() -> float:
        y = pdf.get_y()
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*SUAVE)
        for i, mes in enumerate(meses):
            if i % paso:
                continue
            etiqueta = MESES[mes.month - 1] + (f" {mes.year}" if mes.month == 1 or i == 0 else "")
            pdf.set_xy(x_de(mes), y)
            pdf.cell(0, 4, etiqueta)
        return y + 5

    y = encabezado()
    for p in plan["parcelas"]:
        if y + ALTO_FILA > pdf.h - MARGEN_INFERIOR:
            pdf.add_page()
            pdf.set_y(pdf.t_margin)
            y = encabezado()
        pdf.set_fill_color(*FONDO)
        pdf.rect(x0, y, ancho, ALTO_FILA - 1, style="F")
        pdf.set_draw_color(*BORDE)
        for mes in meses[1:]:
            pdf.line(x_de(mes), y, x_de(mes), y + ALTO_FILA - 1)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TINTA)
        pdf.set_xy(pdf.l_margin, y)
        pdf.cell(ANCHO_ETIQUETA - 2, ALTO_FILA - 1, _recortar(pdf, p["nombre"], ANCHO_ETIQUETA - 3))
        for s in p["siembras"]:
            xa = x_de(date.fromisoformat(s["fecha_siembra"]))
            xb = x_de(date.fromisoformat(s["fecha_cosecha"])) + ancho / total_dias  # el día de cosecha cuenta completo
            pdf.set_fill_color(*PALETA[s["cultivo"]["id"] % len(PALETA)])
            pdf.rect(xa, y + 0.8, xb - xa, ALTO_FILA - 2.6, style="F")
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_text_color(*TINTA)
            pdf.set_xy(xa + 1, y)
            pdf.cell(max(xb - xa - 2, 0), ALTO_FILA - 1, _recortar(pdf, s["cultivo"]["nombre"], xb - xa - 2))
        y += ALTO_FILA

    # Leyenda: un recuadro de color por cada cultivo del plan
    cultivos = {s["cultivo"]["id"]: s["cultivo"]["nombre"] for _, s in pares}
    x, y = pdf.l_margin, y + 3
    pdf.set_font("Helvetica", "", 7.5)
    for cid, nombre in cultivos.items():
        necesita = 6 + pdf.get_string_width(_t(nombre)) + 6
        if x + necesita > pdf.l_margin + pdf.epw:
            x, y = pdf.l_margin, y + 5
        pdf.set_fill_color(*PALETA[cid % len(PALETA)])
        pdf.rect(x, y + 0.6, 4, 3, style="F")
        pdf.set_text_color(*TINTA)
        pdf.set_xy(x + 5.5, y)
        pdf.cell(necesita - 6, 4.2, _t(nombre))
        x += necesita
    pdf.set_y(y + 8)


def _tabla_de_parcela(pdf: _Documento, parcela: dict) -> None:
    if pdf.get_y() + 30 > pdf.h - MARGEN_INFERIOR:  # no dejar el título de una parcela solo al pie de la página
        pdf.add_page()
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*TINTA)
    pdf.cell(0, 7, _t(f"{parcela['nombre']}  -  {parcela['hectareas']:g} ha"), new_x="LMARGIN", new_y="NEXT")
    if not parcela["siembras"]:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*SUAVE)
        pdf.cell(0, 6, "No crops planned in this plot.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        return

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*TINTA)
    pdf.set_fill_color(255, 255, 255)  # las filas sin color propio se rellenan con el color actual: que sea blanco
    encabezados = ("Crop", "Planting", "Harvest", "Days", "Hectares", "Est. income", "Est. cost", "Est. profit")
    with pdf.table(
        col_widths=(62, 30, 30, 16, 24, 38, 38, 39),
        text_align=("LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"),
        headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=VERDE),
        line_height=5.5,
        borders_layout="HORIZONTAL_LINES",
        cell_fill_color=FONDO,  # cebra suave
        cell_fill_mode="EVEN_ROWS",
    ) as tabla:
        fila = tabla.row()
        for h in encabezados:
            fila.cell(h)
        for s in parcela["siembras"]:
            inicio, fin = date.fromisoformat(s["fecha_siembra"]), date.fromisoformat(s["fecha_cosecha"])
            fila = tabla.row()
            for valor in (
                _t(s["cultivo"]["nombre"]), _fecha(s["fecha_siembra"]), _fecha(s["fecha_cosecha"]),
                str((fin - inicio).days + 1), f"{s['hectareas']:g}",
                _pesos(s["ingreso_estimado"]), _pesos(s["costo_total"]), _pesos(s["ganancia_estimada"]),
            ):
                fila.cell(valor)
    pdf.ln(5)


def exportar_pdf(con, plan_id: int, hoy: date) -> tuple[str, bytes]:
    """Devuelve (nombre de archivo, contenido PDF) del plan, con sus cifras a la fecha `hoy`."""
    plan = obtener_plan(con, plan_id)
    resumen = plan_servicio.resumen_plan(plan, hoy)
    abiertas = tareas.conteo_plan(con, plan_id, hoy)

    pdf = _Documento(plan["nombre"])
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*TINTA)
    pdf.cell(0, 10, _recortar(pdf, plan["nombre"], pdf.epw), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SUAVE)
    pdf.cell(0, 5, f"Crop plan - exported on {_fecha(hoy.isoformat())}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    _resumen(pdf, plan, resumen, abiertas)
    _linea_de_tiempo(pdf, plan)
    for parcela in plan["parcelas"]:
        _tabla_de_parcela(pdf, parcela)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*SUAVE)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0, 4,
        "Economic figures are estimates from the data entered for each planting, not a forecast. "
        "Plantings without yield, price or cost show '-'.",
        new_x="LMARGIN", new_y="NEXT",
    )
    base = re.sub(r"[^a-z0-9]+", "-", clave(plan["nombre"])).strip("-") or "plan"
    return f"{base}.pdf", bytes(pdf.output())
