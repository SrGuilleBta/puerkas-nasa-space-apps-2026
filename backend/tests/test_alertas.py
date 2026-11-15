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

    # ---- helada y calor según lo que tolera cada cultivo ----
    def con_ficha(self, nombre, tipo, catalogo_id, minimo, maximo):
        a = activo(nombre, tipo)
        a["cultivo"]["catalogo_id"] = catalogo_id
        return a, {catalogo_id: {"temperatura_absoluta_c": [minimo, maximo]}}

    def test_helada_por_cultivo_usa_el_limite_de_cada_uno(self):
        trigo, f1 = self.con_ficha("Trigo", "cereal", "trigo", 6, 30)
        maiz, f2 = self.con_ficha("Maiz", "cereal", "maiz", 10, 47)
        c = clima([dia("2026-11-12", tmin=8)])  # 8 °C: cerca del límite del trigo (6), por debajo del maíz (10)
        r = alertas.calcular(c, [trigo, maiz], HOY, {**f1, **f2})
        helada = next(a for a in r if a["id"] == "helada")
        self.assertEqual(sorted(helada["cultivos"]), ["Maiz", "Trigo"])
        self.assertEqual(helada["nivel"], "alta")  # el maíz ya está por debajo de su mínimo
        self.assertIn("tolerates down to 10 °C", helada["detalle"])

    def test_un_cultivo_resistente_no_dispara_la_alerta_general(self):
        # 1 °C: el aviso general (<= 2 °C) saltaría, pero la avena tolera -5 °C
        avena, f = self.con_ficha("Avena", "cereal", "avena", -5, 30)
        c = clima([dia("2026-11-12", tmin=1)])
        self.assertNotIn("helada", ids(alertas.calcular(c, [avena], HOY, f)))

    def test_calor_por_cultivo(self):
        trigo, f = self.con_ficha("Trigo", "cereal", "trigo", 6, 30)
        c = clima([dia("2026-11-12", tmax=33)])  # 33 °C: pasa el máximo del trigo (30)
        calor = next(a for a in alertas.calcular(c, [trigo], HOY, f) if a["id"] == "calor")
        self.assertEqual(calor["nivel"], "alta")
        self.assertEqual(calor["cultivos"], ["Trigo"])
        # sin ficha, 33 °C no alcanza el umbral general (35 °C)
        self.assertNotIn("calor", ids(alertas.calcular(c, [activo("Otro", "cereal")], HOY)))

    def test_aviso_de_margen_es_media(self):
        trigo, f = self.con_ficha("Trigo", "cereal", "trigo", 6, 30)
        c = clima([dia("2026-11-12", tmin=8)])  # a 2 °C de su mínimo, dentro del margen de 3
        helada = next(a for a in alertas.calcular(c, [trigo], HOY, f) if a["id"] == "helada")
        self.assertEqual(helada["nivel"], "media")

    def test_cultivo_sin_ficha_usa_el_umbral_general(self):
        c = clima([dia("2026-11-12", tmin=1)])
        r = alertas.calcular(c, [activo("Propio", "otro")], HOY)
        self.assertEqual(next(a for a in r if a["id"] == "helada")["cultivos"], ["Propio"])

    def test_el_mismo_cultivo_en_dos_parcelas_cuenta_una_vez(self):
        trigo, f = self.con_ficha("Trigo", "cereal", "trigo", 6, 30)
        c = clima([dia("2026-11-12", tmin=4)])
        helada = next(a for a in alertas.calcular(c, [trigo, trigo], HOY, f) if a["id"] == "helada")
        self.assertEqual(helada["cultivos"], ["Trigo"])

    # ---- lluvia: déficit y encharcamiento por cultivo ----
    def con_agua(self, nombre, ciclo, lluvia_ideal, encharcamiento=None, catalogo_id="x"):
        a = activo(nombre, "cereal")
        a["cultivo"]["catalogo_id"] = catalogo_id
        ficha = {"ciclo_dias": ciclo, "agua": {"lluvia_optima_mm": lluvia_ideal}}
        if encharcamiento:
            ficha["tolerancia_encharcamiento"] = encharcamiento
        return a, {catalogo_id: ficha}

    def test_deficit_de_lluvia_alto_medio_y_sin_alerta(self):
        maiz, f = self.con_agua("Maiz", [100, 100], [500, 1000])  # necesita 5 mm al día
        c = clima([dia("2026-11-12")])
        # 30 días con 60 mm = 2 mm al día: 40% de lo necesario -> alta
        r = alertas.calcular(c, [maiz], HOY, f, {"dias": 30, "lluviaMm": 60})
        sequia = next(a for a in r if a["id"] == "sequia")
        self.assertEqual((sequia["nivel"], sequia["cultivos"]), ("alta", ["Maiz"]))
        self.assertIn("2.0 mm a day", sequia["detalle"])
        # 3.5 mm al día = 70% -> media
        r = alertas.calcular(c, [maiz], HOY, f, {"dias": 30, "lluviaMm": 105})
        self.assertEqual(next(a for a in r if a["id"] == "sequia")["nivel"], "media")
        # 4 mm al día = 80% -> sin alerta
        r = alertas.calcular(c, [maiz], HOY, f, {"dias": 30, "lluviaMm": 120})
        self.assertNotIn("sequia", ids(r))

    def test_sin_suficientes_dias_de_lluvia_observada_no_juzga(self):
        maiz, f = self.con_agua("Maiz", [100, 100], [500, 1000])
        c = clima([dia("2026-11-12")])
        self.assertNotIn("sequia", ids(alertas.calcular(c, [maiz], HOY, f, {"dias": 5, "lluviaMm": 0})))
        self.assertNotIn("sequia", ids(alertas.calcular(c, [maiz], HOY, f, None)))

    def test_sin_dato_de_lluvia_del_cultivo_o_perenne_no_hay_sequia(self):
        c = clima([dia("2026-11-12")])
        self.assertNotIn("sequia", ids(alertas.calcular(c, [activo("Propio", "otro")], HOY, {}, {"dias": 30, "lluviaMm": 0})))
        perenne, f = self.con_agua("Aguacate", [100, 100], [500, 1000])
        f["x"]["perenne"] = True
        self.assertNotIn("sequia", ids(alertas.calcular(c, [perenne], HOY, f, {"dias": 30, "lluviaMm": 0})))

    def test_avisa_si_viene_lluvia_antes_de_regar(self):
        maiz, f = self.con_agua("Maiz", [100, 100], [500, 1000])
        c = clima([dia("2026-11-12", lluvia=90)])
        sequia = next(a for a in alertas.calcular(c, [maiz], HOY, f, {"dias": 30, "lluviaMm": 10}) if a["id"] == "sequia")
        self.assertIn("check again before irrigating", sequia["detalle"])

    def test_encharcamiento_solo_para_cultivos_sensibles(self):
        sensible, f1 = self.con_agua("Frijol", [100, 100], [500, 1000], "sensible", "frijol")
        resistente, f2 = self.con_agua("Arroz", [100, 100], [500, 1000], "tolera", "arroz")
        c = clima([dia("2026-11-12", lluvia=85)])
        r = alertas.calcular(c, [sensible, resistente], HOY, {**f1, **f2})
        enc = next(a for a in r if a["id"] == "encharcamiento")
        self.assertEqual(enc["cultivos"], ["Frijol"])
        # también con el catálogo ya traducido
        ingles, f3 = self.con_agua("Beans", [100, 100], [500, 1000], "sensitive", "beans")
        self.assertIn("encharcamiento", ids(alertas.calcular(c, [ingles], HOY, f3)))
        # sin lluvia fuerte no hay aviso
        poco = clima([dia("2026-11-12", lluvia=40)])
        self.assertNotIn("encharcamiento", ids(alertas.calcular(poco, [sensible], HOY, f1)))

    def test_suelo_seco_avisa_por_si_solo(self):
        c = clima([dia("2026-11-11"), dia("2026-11-12")])
        suelo = {"percentil": 8.0, "categoria": "D2", "humedad": 12.0, "normal": 20.0}
        r = alertas.calcular(c, [activo("Trigo", "cereal")], HOY, suelo=suelo)
        self.assertEqual(ids(r), ["sequia"])
        self.assertEqual(r[0]["nivel"], "alta")
        self.assertEqual(r[0]["cultivos"], ["Trigo"])

    def test_suelo_normal_o_sin_cultivos_no_avisa(self):
        c = clima([dia("2026-11-11")])
        normal = {"percentil": 55.0, "categoria": None, "humedad": 20.0, "normal": 19.0}
        seco = {"percentil": 8.0, "categoria": "D2", "humedad": 12.0, "normal": 20.0}
        self.assertEqual(alertas.calcular(c, [activo("Trigo", "cereal")], HOY, suelo=normal), [])
        self.assertEqual(alertas.calcular(c, [], HOY, suelo=seco), [])

    def test_suelo_seco_se_suma_al_deficit_de_lluvia(self):
        c = clima([dia("2026-11-11")])
        suelo = {"percentil": 25.0, "categoria": "D0", "humedad": 15.0, "normal": 19.0}
        r = alertas.calcular(c, [activo("Trigo", "cereal")], HOY, suelo=suelo)
        self.assertEqual(r[0]["nivel"], "media")
        self.assertIn("NASA SMAP", r[0]["detalle"])


if __name__ == "__main__":
    unittest.main()
