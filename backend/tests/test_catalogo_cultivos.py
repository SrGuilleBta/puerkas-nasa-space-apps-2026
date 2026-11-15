import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Antes de importar la app: así config.DB_PATH apunta a una base temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from app import config, db  # noqa: E402
from app.services import catalogo_cultivos  # noqa: E402
from app.services.planificador import NoEncontrado  # noqa: E402

FALSO = {
    "cultivos": [],
    "por_id": {
        "maiz-grano": {
            "id": "maiz-grano", "nombre": "Maíz grano", "tipo": "Cereal", "ciclo_dias": [120, 150],
            "perenne": False, "cientifico": "Zea mays", "familia": "Poaceae", "fija_nitrogeno": False,
            "descripcion": "Base.", "suelo": "Francos.", "cuidados": ["Riega."],
            "temperatura_optima_c": [18, 33], "ph_optimo": [5, 7],
            "agua": {"consumo": "medio", "lluvia_optima_mm": [600, 1200]},
            "nacional": {"rend_p50": 3.8}, "fuentes": ["SIAP"],
        },
        "papa": {"id": "papa", "nombre": "Papa", "tipo": "Tubérculo", "ciclo_dias": [90, 120], "perenne": False},
        "aguacate": {"id": "aguacate", "nombre": "Aguacate", "tipo": "Frutal", "ciclo_dias": None, "perenne": True},
        "semilla-x": {"id": "semilla-x", "nombre": "Semilla X", "tipo": "Semilla", "ciclo_dias": [10, 20]},
    },
}
FALSO["cultivos"] = list(FALSO["por_id"].values())


class PruebasCatalogoCultivos(unittest.TestCase):
    def setUp(self):
        self.ruta = Path(tempfile.mkdtemp()) / "catalogo.db"
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

    def test_normaliza_tipo_y_ciclo(self):
        self.assertEqual(catalogo_cultivos.tipo_del_planificador("Tubérculo"), "tuberculo")
        self.assertEqual(catalogo_cultivos.tipo_del_planificador("Semilla"), "otro")
        self.assertEqual(catalogo_cultivos.tipo_del_planificador(None), "otro")
        self.assertEqual(catalogo_cultivos.ciclo_de(FALSO["por_id"]["maiz-grano"]), 135)
        self.assertEqual(catalogo_cultivos.ciclo_de(FALSO["por_id"]["aguacate"]), 365)

    def test_lista_ordenada_sin_acentos(self):
        nombres = [c["nombre"] for c in catalogo_cultivos.listar()]
        self.assertEqual(nombres, ["Aguacate", "Maíz grano", "Papa", "Semilla X"])

    def test_migracion_v4_enlaza_los_cultivos_de_demo(self):
        fila = self.con.execute("SELECT nombre, catalogo_id FROM cultivo WHERE catalogo_id = 'maiz-grano'").fetchone()
        self.assertEqual(fila["nombre"], "Maíz grano")
        self.assertEqual(self.con.execute("PRAGMA user_version").fetchone()[0], db.VERSION_ESQUEMA)

    def test_asegurar_reutiliza_el_enlazado(self):
        antes = self.con.execute("SELECT COUNT(*) FROM cultivo").fetchone()[0]
        c = catalogo_cultivos.asegurar_cultivo(self.con, "maiz-grano")
        self.assertEqual(c["nombre"], "Maíz grano")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM cultivo").fetchone()[0], antes)

    def test_asegurar_crea_con_tipo_y_ciclo_del_catalogo(self):
        c = catalogo_cultivos.asegurar_cultivo(self.con, "papa")
        self.assertEqual((c["nombre"], c["tipo"], c["ciclo_dias"]), ("Papa", "tuberculo", 105))
        self.assertEqual(catalogo_cultivos.asegurar_cultivo(self.con, "papa")["id"], c["id"])  # no duplica

    def test_asegurar_enlaza_un_cultivo_del_usuario_con_el_mismo_nombre(self):
        with self.con:
            id_ = self.con.execute(
                "INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES ('papa', ?, 'otro', 80)",
                (db.clave("papa"),),
            ).lastrowid
        c = catalogo_cultivos.asegurar_cultivo(self.con, "papa")
        self.assertEqual(c["id"], id_)
        self.assertEqual(self.con.execute("SELECT catalogo_id FROM cultivo WHERE id = ?", (id_,)).fetchone()[0], "papa")

    def test_asegurar_con_id_desconocido(self):
        with self.assertRaises(NoEncontrado):
            catalogo_cultivos.asegurar_cultivo(self.con, "no-existe")

    def test_ficha(self):
        maiz = catalogo_cultivos.asegurar_cultivo(self.con, "maiz-grano")
        f = catalogo_cultivos.ficha(self.con, maiz["id"])
        self.assertEqual(f["nombreCientifico"], "Zea mays")
        self.assertEqual(f["cuidados"], ["Riega."])
        self.assertEqual(f["temperaturaOptimaC"], [18, 33])
        self.assertEqual(f["rendimientoNacionalTHa"], 3.8)

    def test_ficha_de_un_cultivo_que_no_viene_del_catalogo(self):
        with self.con:
            id_ = self.con.execute(
                "INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES ('Propio', 'propio', 'otro', 50)"
            ).lastrowid
        self.assertIsNone(catalogo_cultivos.ficha(self.con, id_))

    def test_migracion_v4_en_base_antigua_no_toca_cultivos_del_usuario(self):
        ruta = Path(tempfile.mkdtemp()) / "v3.db"
        con = sqlite3.connect(ruta)
        con.executescript(db.ESQUEMA + db.MIGRACION_UBICACIONES)
        con.execute("INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES ('Maíz amarillo', ?, 'cereal', 125)", (db.clave("Maíz amarillo"),))
        con.execute("INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES ('Mi cultivo', 'mi cultivo', 'otro', 60)")
        con.execute("PRAGMA user_version = 3")
        con.commit()
        con.close()
        with patch.object(config, "DB_PATH", ruta):
            db.iniciar()
            con = db.conectar()
            nombres = {f["nombre"]: f["catalogo_id"] for f in con.execute("SELECT nombre, catalogo_id FROM cultivo")}
            con.close()
        self.assertEqual(nombres, {"Maíz grano": "maiz-grano", "Mi cultivo": None})


if __name__ == "__main__":
    unittest.main()
