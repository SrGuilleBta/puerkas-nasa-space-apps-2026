import unittest

from app.services import ventana_siembra

TEMP = [10, 12, 15, 19, 22, 25, 26, 25, 22, 18, 13, 11]  # enero a diciembre
LLUVIA = [20, 20, 30, 40, 80, 120, 150, 140, 120, 60, 30, 20]


def ficha(**extra):
    base = {
        "id": "x", "nombre": "X", "ciclo_dias": [90, 90], "perenne": False,
        "temperatura_optima_c": [18, 33], "temperatura_absoluta_c": [10, 47],
        "agua": {"consumo": "medio", "lluvia_optima_mm": [200, 400]},
    }
    base.update(extra)
    return base


def por_mes(r):
    return {m["mes"]: m for m in r["meses"]}


class PruebasVentanaSiembra(unittest.TestCase):
    def test_un_cultivo_perenne_no_tiene_mes_de_siembra(self):
        r = ventana_siembra.calcular(ficha(perenne=True), TEMP, LLUVIA)
        self.assertFalse(r["estacional"])
        self.assertEqual(r["mejores"], [])

    def test_sin_rango_de_temperatura_no_calcula(self):
        self.assertFalse(ventana_siembra.calcular(ficha(temperatura_optima_c=None), TEMP, LLUVIA)["estacional"])

    def test_mejores_meses_y_niveles(self):
        r = ventana_siembra.calcular(ficha(), TEMP, LLUVIA)
        meses = por_mes(r)
        self.assertEqual(r["mesesDelCiclo"], 3)
        self.assertEqual(meses[5]["nivel"], "good")  # mayo a julio: 22, 25, 26 °C
        self.assertEqual(meses[12]["nivel"], "poor")  # diciembre a febrero: 11, 10, 12 °C
        self.assertIn(5, r["mejores"])
        self.assertNotIn(12, r["mejores"])
        self.assertEqual(r["nivelMejores"], "good")

    def test_el_ciclo_da_la_vuelta_al_ano(self):
        # Siembra en noviembre: noviembre, diciembre y enero (13, 11, 10 °C)
        m = por_mes(ventana_siembra.calcular(ficha(), TEMP, LLUVIA))[11]
        self.assertEqual(m["tempMedia"], 11.3)

    def test_un_mes_fuera_de_lo_tolerable_hace_malo_el_inicio(self):
        frio = [-5] + TEMP[1:]
        m = por_mes(ventana_siembra.calcular(ficha(), frio, LLUVIA))
        self.assertEqual(m[12]["nivel"], "poor")  # el ciclo de diciembre pasa por un enero de -5 °C

    def test_puntaje_gradual_entre_lo_ideal_y_lo_tolerable(self):
        # Mes frío pero tolerable: puntaje intermedio, "fair" si el resto está en lo ideal
        temp = [14] * 12
        r = ventana_siembra.calcular(ficha(), temp, LLUVIA)
        puntaje = r["meses"][0]["puntaje"]
        self.assertGreater(puntaje, 0.4)
        self.assertLess(puntaje, 1)

    def test_avisa_si_la_lluvia_del_ciclo_no_alcanza(self):
        r = por_mes(ventana_siembra.calcular(ficha(), TEMP, LLUVIA))
        self.assertTrue(r[1]["necesitaRiego"])  # enero a marzo: 70 mm contra 200 mm
        self.assertFalse(r[6]["necesitaRiego"])  # junio a agosto: 410 mm

    def test_si_ningun_mes_es_bueno_se_ofrecen_los_regulares(self):
        r = ventana_siembra.calcular(ficha(temperatura_optima_c=[27, 33]), TEMP, LLUVIA)
        if not any(m["nivel"] == "good" for m in r["meses"]):
            self.assertEqual(r["nivelMejores"], "fair" if r["mejores"] else None)


if __name__ == "__main__":
    unittest.main()
