import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

# Antes de importar la app: así config.DB_PATH apunta a una base temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from app import config, db  # noqa: E402
from app.services import catalogo_cultivos, rotacion  # noqa: E402

HOY = date(2026, 11, 15)


def c(id_, nombre, tipo, familia=None, fija=None, area=100, perenne=False, ciclos=("PV",)):
    return {"id": id_, "nombre": nombre, "tipo": tipo, "familia": familia, "fija_nitrogeno": fija,
            "ciclo_dias": [90, 120], "perenne": perenne, "ciclos_practicados": list(ciclos),
            "nacional": {"superficie_sembrada_prom_ha": area}}


LISTA = [
    c("maiz", "Maíz", "Cereal", "Poaceae", False, 7000),
    c("trigo", "Trigo", "Cereal", "Poaceae", False, 500),
    c("semilla-maiz", "Semilla de maíz", "Cereal", "Poaceae", False, 9000),  # nunca se sugiere una semilla
    c("avena-perenne", "Pasto cereal", "Cereal", "Poaceae", False, 9000, perenne=True),
    c("frijol", "Frijol", "Leguminosa", "Fabaceae", True, 1500),
    c("garbanzo", "Garbanzo", "Leguminosa", "Fabaceae", True, 100),
    c("lenteja", "Lenteja", "Leguminosa", None, None, 9999),  # sin marca de fijación: no se sugiere
    c("jitomate", "Jitomate", "Hortaliza", "Solanaceae", False, 50),
]
FALSO = {"cultivos": LISTA, "por_id": {x["id"]: x for x in LISTA}}


def cultivo(id_catalogo, nombre, tipo, id_=None):
    return {"id": id_ or 900, "nombre": nombre, "tipo": tipo, "catalogo_id": id_catalogo}


def parcela(*cultivos):
    siembras = [
        {"cultivo": cu, "fecha_siembra": f"2026-0{i + 1}-01", "fecha_cosecha": f"2026-0{i + 1}-28"}
        for i, cu in enumerate(cultivos)
    ]
    return {"id": 1, "nombre": "Lote", "siembras": siembras}


class PruebasRotacion(unittest.TestCase):
    def setUp(self):
        self.ruta = Path(tempfile.mkdtemp()) / "rotacion.db"
        self.p1 = patch.object(config, "DB_PATH", self.ruta)
        self.p2 = patch.object(catalogo_cultivos, "_catalogo", lambda: FALSO)
        self.p1.start()
        self.p2.start()
        db.iniciar()
        self.con = db.conectar()

    def tearDown(self):
        self.con.close()
        self.p2.stop()
        self.p1.stop()

    def recomendar(self, *cultivos):
        r = rotacion.recomendaciones(self.con, {"parcelas": [parcela(*cultivos)]}, HOY)
        return r[0] if r else None

    def test_despues_de_una_leguminosa_un_cereal_el_de_mayor_superficie(self):
        r = self.recomendar(cultivo("frijol", "Frijol", "leguminosa"))
        self.assertEqual(r["sugerido"]["catalogo_id"], "maiz")
        self.assertIn("Fabaceae", r["razon"])
        self.assertIn("nitrogen", r["razon"])

    def test_prefiere_el_cereal_que_menos_se_ha_sembrado_en_la_parcela(self):
        r = self.recomendar(cultivo("maiz", "Maíz", "cereal"), cultivo("frijol", "Frijol", "leguminosa"))
        self.assertEqual(r["sugerido"]["catalogo_id"], "trigo")

    def test_despues_de_un_cereal_una_leguminosa_que_fije_nitrogeno(self):
        r = self.recomendar(cultivo("maiz", "Maíz", "cereal"))
        self.assertEqual(r["sugerido"]["catalogo_id"], "frijol")  # la lenteja sin marca no entra
        self.assertIn("Replenishes", r["razon"])

    def test_despues_de_una_hortaliza_tambien_una_leguminosa(self):
        self.assertEqual(self.recomendar(cultivo("jitomate", "Jitomate", "hortaliza"))["sugerido"]["catalogo_id"], "frijol")

    def test_nunca_semillas_ni_cultivos_perennes(self):
        for _ in range(2):
            r = self.recomendar(cultivo("frijol", "Frijol", "leguminosa"))
            self.assertNotIn(r["sugerido"]["catalogo_id"], ("semilla-maiz", "avena-perenne"))

    def test_un_cultivo_que_ya_esta_en_el_planificador_trae_su_id(self):
        with self.con:
            self.con.execute("INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias, catalogo_id) VALUES ('Maíz', 'maiz', 'cereal', 120, 'maiz')")
        previo = self.con.execute("SELECT id FROM cultivo WHERE catalogo_id = 'maiz'").fetchone()[0]
        r = self.recomendar(cultivo("frijol", "Frijol", "leguminosa"))
        self.assertEqual(r["sugerido"]["id"], previo)

    def test_un_cultivo_nuevo_del_catalogo_no_tiene_id(self):
        self.assertIsNone(self.recomendar(cultivo("frijol", "Frijol", "leguminosa"))["sugerido"]["id"])

    def test_sin_catalogo_en_el_ultimo_cultivo_usa_la_regla_por_tipo(self):
        with self.con:
            self.con.execute("INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES ('Mi cereal', 'mi cereal', 'cereal', 100)")
        propio = self.con.execute("SELECT * FROM cultivo WHERE clave = 'mi cereal'").fetchone()
        r = self.recomendar(cultivo(None, propio["nombre"], "cereal", id_=propio["id"]))
        self.assertIsNotNone(r)
        self.assertEqual(r["sugerido"]["tipo"], "leguminosa")
        self.assertIn("Replenishes", r["razon"])

    def test_los_frutales_y_forrajes_no_rotan(self):
        self.assertIsNone(self.recomendar(cultivo("jitomate", "Pasto", "forraje")))


if __name__ == "__main__":
    unittest.main()
