import unittest

from app.services import nasa_power


class PruebasNasaPower(unittest.TestCase):
    def test_resume_y_ignora_dias_sin_dato(self):
        serie = {
            "T2M": {"20261001": 20.0, "20261002": 10.0, "20261003": -999},
            "T2M_MAX": {"20261001": 28.0, "20261002": 25.0, "20261003": -999},
            "T2M_MIN": {"20261001": 12.0, "20261002": 3.5, "20261003": -999},
            "PRECTOTCORR": {"20261001": 0.0, "20261002": 12.4, "20261003": 0.5},
            "ALLSKY_SFC_SW_DWN": {"20261001": 5.0, "20261002": 4.0, "20261003": -999},
            "GWETROOT": {"20261001": 0.4, "20261002": 0.6, "20261003": -999},
        }
        r = nasa_power.resumir(serie)
        self.assertEqual(r["tempMedia"], 15.0)
        self.assertEqual(r["tempMax"], 28.0)
        self.assertEqual(r["tempMin"], 3.5)
        self.assertEqual(r["lluviaMm"], 13)
        self.assertEqual(r["diasConLluvia"], 1)  # 0.5 mm no cuenta como día de lluvia
        self.assertEqual(r["radiacion"], 4.5)
        self.assertEqual(r["humedadRaizPct"], 50)

    def test_sin_datos(self):
        r = nasa_power.resumir({"T2M": {"20261001": -999}})
        self.assertIsNone(r["tempMedia"])
        self.assertIsNone(r["lluviaMm"])
        self.assertIsNone(r["humedadRaizPct"])
        self.assertEqual(r["dias"], 0)


if __name__ == "__main__":
    unittest.main()
