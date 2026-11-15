import unittest
from datetime import date

from app.services import alertas

HOY = date(2026, 11, 11)  # miércoles


def dia(fecha, tmax=24, tmin=12, lluvia=10):
    return {"fecha": fecha, "tmax": tmax, "tmin": tmin, "lluvia": lluvia, "cielo": "sol"}


def clima(dias, temperatura=22, humedad=55, viento=10):
    return {"pronostico": dias, "hoy": {"temperatura": temperatura, "humedad": humedad, "vientoKmh": viento}}


def activo(nombre, tipo):
    return {"cultivo": {"nombre": nombre, "tipo": tipo}}


def ids(lista):
    return [a["id"] for a in lista]


class PruebasAlertas(unittest.TestCase):
    def test_sin_riesgos_no_hay_alertas(self):
        c = clima([dia("2026-11-11"), dia("2026-11-12")])
        self.assertEqual(alertas.calcular(c, [activo("Trigo", "cereal")], HOY), [])

    def test_helada_y_calor(self):
        c = clima([dia("2026-11-12", tmin=-1), dia("2026-11-13", tmax=39)])
        r = alertas.calcular(c, [], HOY)
        self.assertEqual(ids(r), ["helada", "calor"])
        self.assertEqual(r[0]["nivel"], "alta")
        self.assertIn("on Thursday", r[0]["titulo"])  # 2026-11-12 es jueves
        self.assertIn("on Friday", r[1]["titulo"])

    def test_ignora_dias_pasados(self):
        c = clima([dia("2026-11-09", tmin=-5), dia("2026-11-11")])
        self.assertEqual(alertas.calcular(c, [], HOY), [])

    def test_lluvia_y_viento(self):
        c = clima([dia("2026-11-11", lluvia=90)], viento=45)
        self.assertEqual(sorted(ids(alertas.calcular(c, [], HOY))), ["lluvia", "viento"])

    def test_plagas_solo_con_cultivos_activos(self):
        c = clima([dia("2026-11-11", lluvia=70), dia("2026-11-12", lluvia=80)], humedad=85)
        self.assertNotIn("hongos", ids(alertas.calcular(c, [], HOY)))
        r = alertas.calcular(c, [activo("Trigo cristalino", "cereal")], HOY)
        hongos = next(a for a in r if a["id"] == "hongos")
        self.assertEqual(hongos["tipo"], "plaga")
        self.assertEqual(hongos["cultivos"], ["Trigo cristalino"])
        self.assertIn("rust", hongos["detalle"])

    def test_hongos_no_aplican_a_forraje(self):
        c = clima([dia("2026-11-11", lluvia=70)], humedad=90)
        self.assertNotIn("hongos", ids(alertas.calcular(c, [activo("Alfalfa", "forraje")], HOY)))

    def test_chupadores_con_calor_seco(self):
        c = clima([dia("2026-11-11", tmax=34, lluvia=5)], temperatura=30, humedad=35)
        r = alertas.calcular(c, [activo("Jitomate", "hortaliza")], HOY)
        self.assertIn("chupadores", ids(r))

    def test_cogollero_solo_en_maiz(self):
        c = clima([dia("2026-11-11", tmax=31)])
        self.assertIn("cogollero", ids(alertas.calcular(c, [activo("Maíz amarillo", "cereal")], HOY)))
        self.assertNotIn("cogollero", ids(alertas.calcular(c, [activo("Trigo", "cereal")], HOY)))

    def test_orden_por_gravedad(self):
        c = clima([dia("2026-11-11", tmin=-2, lluvia=90)])
        r = alertas.calcular(c, [], HOY)
        self.assertEqual(r[0]["id"], "helada")  # alta antes que media


if __name__ == "__main__":
    unittest.main()
