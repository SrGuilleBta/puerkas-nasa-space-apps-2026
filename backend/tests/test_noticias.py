import unittest
from datetime import date

from app.services import noticias

HOY = date(2026, 11, 14)

RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Old item</title><link>https://ejemplo.org/a</link><pubDate>Mon, 03 Nov 2026 10:00:00 +0000</pubDate>
<description>&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt; What to read next: otra cosa</description></item>
<item><title>New item</title><link>https://ejemplo.org/b</link><pubDate>Fri, 13 Nov 2026 10:00:00 +0000</pubDate><description>Short</description></item>
<item><title>Evil link</title><link>javascript:alert(1)</link></item>
<item><title></title><link>https://ejemplo.org/c</link></item>
</channel></rss>"""


class PruebasNoticias(unittest.TestCase):
    def test_parsea_rss_y_ordena_por_fecha(self):
        r = noticias.parsear_rss(RSS, "Fuente")
        self.assertEqual([i["titulo"] for i in r], ["New item", "Old item"])
        self.assertEqual(r[0]["fecha"], "2026-11-13")
        self.assertEqual(r[0]["categoria"], "research")
        self.assertEqual(r[0]["fuente"], "Fuente")

    def test_tolera_atributos_pegados_como_el_feed_de_nasa(self):
        pegado = RSS.replace('<rss version="2.0">', '<rss version="2.0" xmlns:a="x"xmlns:b="y">')
        self.assertEqual(len(noticias.parsear_rss(pegado, "NASA")), 2)

    def test_limpia_html_y_resto_del_feed(self):
        r = noticias.parsear_rss(RSS, "Fuente")
        self.assertEqual(r[1]["resumen"], "Hello & welcome")

    def test_quita_el_resto_del_feed_de_nasa(self):
        xml = RSS.replace("<description>Short</description>", "<description>A nice story. The post Title appeared first on NASA Science .</description>")
        self.assertEqual(noticias.parsear_rss(xml, "NASA")[0]["resumen"], "A nice story.")

    def test_descarta_enlaces_peligrosos_y_sin_titulo(self):
        r = noticias.parsear_rss(RSS, "Fuente")
        self.assertTrue(all(i["enlace"].startswith("https://") for i in r))
        self.assertEqual(len(r), 2)

    def test_propias_alertas_cosecha_y_lluvia(self):
        alertas = [
            {"id": "helada", "tipo": "clima", "titulo": "Frost", "detalle": "Cold.", "cultivos": []},
            {"id": "hongos", "tipo": "plaga", "titulo": "Fungus", "detalle": "Wet.", "cultivos": ["Trigo"]},
        ]
        activos = [
            {"id": 7, "dias_totales": 100, "dia": 90, "hectareas": 5,
             "cultivo": {"nombre": "Trigo"}, "parcela": {"nombre": "Norte"}},
            {"id": 8, "dias_totales": 100, "dia": 10, "hectareas": 5,
             "cultivo": {"nombre": "Maíz"}, "parcela": {"nombre": "Sur"}},
        ]
        nasa = {"dias": 20, "lluviaMm": 40, "diasConLluvia": 6, "tempMedia": 18.0, "humedadRaizPct": 55}
        r = noticias.propias(alertas, activos, nasa, "Monterrey", HOY)
        por_id = {i["id"]: i for i in r}
        self.assertEqual(por_id["alerta-helada"]["categoria"], "weather")
        self.assertEqual(por_id["alerta-hongos"]["categoria"], "farm")
        self.assertIn("Trigo", por_id["alerta-hongos"]["resumen"])
        self.assertEqual(por_id["cosecha-7"]["titulo"], "Trigo harvest in 10 days")
        self.assertNotIn("cosecha-8", por_id)  # le faltan 90 días
        self.assertIn("40 mm", por_id["nasa-lluvia"]["titulo"])

    def test_propias_avisa_de_tareas_vencidas(self):
        peor = {"titulo": "Fertilize", "cultivo": "Maíz", "parcela": "Sur", "dias_retraso": 12}
        r = noticias.propias([], [], None, "X", HOY, {"total": 3, "tareas": [peor]})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["id"], "tareas-vencidas")
        self.assertEqual(r[0]["titulo"], "3 overdue tasks")
        self.assertEqual((r[0]["categoria"], r[0]["destino"]), ("farm", "planificador"))
        self.assertIn("Fertilize for Maíz · Sur (12 days late)", r[0]["resumen"])

        una = noticias.propias([], [], None, "X", HOY, {"total": 1, "tareas": [{**peor, "dias_retraso": 1}]})
        self.assertEqual(una[0]["titulo"], "1 overdue task")
        self.assertIn("(1 day late)", una[0]["resumen"])

    def test_sin_tareas_vencidas_no_hay_aviso(self):
        self.assertEqual(noticias.propias([], [], None, "X", HOY, {"total": 0, "tareas": []}), [])

    def test_sin_datos_no_inventa_noticias(self):
        self.assertEqual(noticias.propias([], [], None, "X", HOY), [])
        self.assertEqual(noticias.propias([], [], {"dias": 0, "lluviaMm": None}, "X", HOY), [])


if __name__ == "__main__":
    unittest.main()
