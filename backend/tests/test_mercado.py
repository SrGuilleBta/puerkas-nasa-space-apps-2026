"""Pruebas de Mercado: precios al consumidor (Profeco) por estado, con datos de mentira en una carpeta temporal."""

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

# Antes de importar la app: así la base apunta a una carpeta temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import cultivos, mercado, noticias  # noqa: E402

ULTIMO = date(2026, 7, 31)


def dias(desde: date, n: int, precio0: float, paso: float):
    return [[(desde + timedelta(days=i)).isoformat(), round(precio0 + paso * i, 2)] for i in range(n)]


DATOS = {
    "AGUACATE": {
        "nombre": "AVOCADO",
        # un punto semanal viejo (cerca de hace 30 días) y los últimos días reales
        "real": [["2026-06-26", 50.0], ["2026-07-29", 58.0], ["2026-07-30", 59.0], ["2026-07-31", 60.0]],
        # 30 días a 0.2 por día: el 30.º día queda en 66.0
        "proyeccion": dias(date(2026, 8, 1), 30, 60.2, 0.2),
    },
    "JITOMATE": {
        "nombre": "TOMATO",
        "real": [["2026-06-30", 20.0], ["2026-07-31", 19.0]],
        "proyeccion": dias(date(2026, 8, 1), 30, 19.0, 0.0),
    },
}


def escribir_datos(carpeta: Path):
    (carpeta / "estados").mkdir(parents=True)
    meta = {
        "ultimoDatoReal": "2026-07-31",
        "proyeccionHasta": "2026-08-30",
        "fuente": "Profeco de prueba",
        "estados": [
            {"clave": "nuevo_leon", "nombre": "NUEVO LEON", "nombreEn": "NUEVO LEON", "productos": 2},
            {"clave": "mexico", "nombre": "MEXICO", "nombreEn": "STATE OF MEXICO", "productos": 0},
        ],
        "productos": {"AGUACATE": "AVOCADO", "JITOMATE": "TOMATO"},
    }
    (carpeta / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (carpeta / "estados" / "nuevo_leon.json").write_text(
        json.dumps({"estado": "NUEVO LEON", "estadoEn": "NUEVO LEON", "productos": DATOS}), encoding="utf-8"
    )
    (carpeta / "estados" / "mexico.json").write_text(
        json.dumps({"estado": "MEXICO", "estadoEn": "STATE OF MEXICO", "productos": {}}), encoding="utf-8"
    )


class ConDatos(unittest.TestCase):
    def setUp(self):
        self._carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self._carpeta.cleanup)
        escribir_datos(Path(self._carpeta.name))
        parche = patch.object(mercado, "CARPETA", Path(self._carpeta.name))
        parche.start()
        self.addCleanup(parche.stop)
        self.limpiar()
        self.addCleanup(self.limpiar)

    @staticmethod
    def limpiar():
        mercado.meta.cache_clear()
        mercado._estado.cache_clear()
        mercado._producto_de_cultivo.cache_clear()


class PruebasServicio(ConDatos):
    def test_estados_con_la_frescura_de_los_datos(self):
        r = mercado.estados(date(2026, 8, 5))
        self.assertEqual([e["clave"] for e in r["estados"]], ["nuevo_leon", "mexico"])
        self.assertEqual((r["ultimoDatoReal"], r["diasSinDatos"], r["desactualizado"], r["unidad"]), ("2026-07-31", 5, False, "MXN/kg"))
        viejo = mercado.estados(date(2026, 11, 15))
        self.assertEqual((viejo["diasSinDatos"], viejo["desactualizado"]), (107, True))
        self.assertEqual(mercado.estados(date(2026, 7, 1))["diasSinDatos"], 0)  # nunca negativo

    def test_resumen_de_productos_cambio_a_30_dias_y_proyectado(self):
        r = mercado.productos("nuevo_leon", date(2026, 8, 1))
        por_id = {p["id"]: p for p in r["productos"]}
        # 60 contra 50 del 26 de junio (a 5 días de hace 30 días): +20 %; la proyección llega a 66.0 el día 30: +10 %
        self.assertEqual(
            (por_id["AGUACATE"]["precio"], por_id["AGUACATE"]["fecha"], por_id["AGUACATE"]["cambio30dPct"], por_id["AGUACATE"]["proyeccion30dPct"]),
            (60.0, "2026-07-31", 20.0, 10.0),
        )
        self.assertEqual((por_id["JITOMATE"]["cambio30dPct"], por_id["JITOMATE"]["proyeccion30dPct"]), (-5.0, 0.0))
        self.assertEqual([p["nombre"] for p in r["productos"]], ["AVOCADO", "TOMATO"])  # por nombre

    def test_sin_un_punto_cercano_a_hace_30_dias_no_inventa_el_cambio(self):
        DATOS_VIEJO = {"AGUACATE": {"nombre": "AVOCADO", "real": [["2026-03-01", 40.0], ["2026-07-31", 60.0]], "proyeccion": []}}
        ruta = Path(self._carpeta.name) / "estados" / "nuevo_leon.json"
        ruta.write_text(json.dumps({"estado": "NUEVO LEON", "estadoEn": "NUEVO LEON", "productos": DATOS_VIEJO}), encoding="utf-8")
        self.limpiar()
        p = mercado.productos("nuevo_leon", date(2026, 8, 1))["productos"][0]
        self.assertEqual((p["precio"], p["cambio30dPct"], p["proyeccion30dPct"]), (60.0, None, None))

    def test_serie_de_una_semana_une_lo_real_con_la_proyeccion(self):
        r = mercado.serie("nuevo_leon", ["AGUACATE"], "semana", date(2026, 8, 1))
        self.assertEqual((r["desde"], r["hasta"]), ("2026-07-24", "2026-08-07"))
        puntos = r["productos"][0]["puntos"]
        self.assertEqual([p["fecha"] for p in puntos][:3], ["2026-07-29", "2026-07-30", "2026-07-31"])
        self.assertEqual(puntos[-1]["fecha"], "2026-08-07")
        corte = next(p for p in puntos if p["fecha"] == "2026-07-31")
        self.assertEqual((corte["real"], corte["proyeccion"]), (60.0, 60.0))  # las dos líneas se tocan en el último dato real
        primero_proyectado = next(p for p in puntos if p["fecha"] == "2026-08-01")
        self.assertEqual((primero_proyectado["real"], primero_proyectado["proyeccion"]), (None, 60.2))

    def test_serie_de_un_anio_llega_hasta_el_final_de_la_proyeccion(self):
        r = mercado.serie("nuevo_leon", ["AGUACATE", "JITOMATE"], "anio", date(2026, 8, 1))
        self.assertEqual(r["hasta"], "2026-08-30")
        self.assertEqual([p["id"] for p in r["productos"]], ["AGUACATE", "JITOMATE"])
        self.assertEqual(r["productos"][0]["puntos"][0]["fecha"], "2026-06-26")

    def test_productos_repetidos_o_inexistentes_y_rangos_desconocidos(self):
        self.assertEqual(len(mercado.serie("nuevo_leon", ["AGUACATE", "AGUACATE"], "mes", date(2026, 8, 1))["productos"]), 1)
        with self.assertRaises(mercado.SinDatos):
            mercado.serie("nuevo_leon", ["NOEXISTE"], "mes", date(2026, 8, 1))
        with self.assertRaises(mercado.SinDatos):
            mercado.serie("nuevo_leon", ["AGUACATE"], "decada", date(2026, 8, 1))

    def test_estado_desconocido_o_con_ruta_peligrosa(self):
        for clave in ("no_existe", "../meta", "", "NUEVO LEON"):
            with self.assertRaises(mercado.SinDatos, msg=clave):
                mercado.productos(clave, date(2026, 8, 1))

    def test_estado_de_una_ubicacion_por_su_clave_inegi(self):
        self.assertEqual(mercado.clave_de_estado("19"), "nuevo_leon")  # Nuevo León
        self.assertEqual(mercado.clave_de_estado("15"), "mexico")  # México (el estado, no el país)
        self.assertIsNone(mercado.clave_de_estado("02"))  # Baja California existe en INEGI, pero estos datos de prueba no lo traen
        self.assertIsNone(mercado.clave_de_estado(None))
        self.assertIsNone(mercado.clave_de_estado("99"))

    def catalogo_falso(self):
        return {"cultivos": [
            {"id": "aguacate", "nombre": "Avocado", "nombre_es": "Aguacate"},
            {"id": "tomate-rojo-jitomate", "nombre": "Tomato", "nombre_es": "Tomate rojo (jitomate)"},
            {"id": "tomate-verde", "nombre": "Tomatillo", "nombre_es": "Tomate verde"},
        ]}

    def test_cultivo_del_catalogo_con_su_producto_por_nombre_o_por_excepcion(self):
        with patch.object(cultivos, "catalogo", return_value=self.catalogo_falso()):
            self.assertEqual(mercado.producto_de_cultivo("aguacate"), "AGUACATE")  # mismo nombre
            self.assertEqual(mercado.producto_de_cultivo("tomate-rojo-jitomate"), "JITOMATE")  # excepción
            self.assertIsNone(mercado.producto_de_cultivo("tomate-verde"))  # TOMATE no está en estos datos
            self.assertIsNone(mercado.producto_de_cultivo("maiz-grano"))
            self.assertIsNone(mercado.producto_de_cultivo(None))

    def test_tendencia_de_un_cultivo_en_su_estado(self):
        with patch.object(cultivos, "catalogo", return_value=self.catalogo_falso()):
            t = mercado.tendencia("aguacate", "nuevo_leon", date(2026, 11, 15))
            self.assertEqual((t["precio"], t["estado"], t["producto"], t["cambio30dPct"]), (60.0, "NUEVO LEON", "AGUACATE", 20.0))
            self.assertTrue(t["desactualizado"])
            self.assertEqual(t["unidad"], "MXN/kg")
            self.assertIsNone(mercado.tendencia("aguacate", "mexico", date(2026, 8, 1)))  # ese estado no lo trae
            self.assertIsNone(mercado.tendencia("aguacate", None, date(2026, 8, 1)))
            self.assertIsNone(mercado.tendencia("aguacate", "no_existe", date(2026, 8, 1)))
            self.assertIsNone(mercado.tendencia("maiz-grano", "nuevo_leon", date(2026, 8, 1)))

    def test_sin_datos_generados_nada_truena(self):
        with patch.object(mercado, "CARPETA", Path(self._carpeta.name) / "no-existe"):
            self.limpiar()
            with self.assertRaises(mercado.SinDatos):
                mercado.estados(date(2026, 8, 1))
            self.assertIsNone(mercado.tendencia("aguacate", "nuevo_leon", date(2026, 8, 1)))
            self.assertIsNone(mercado.producto_de_cultivo("aguacate"))


class PruebasNoticiaDePrecio(unittest.TestCase):
    def tendencia(self, **cambios):
        t = {"producto": "AGUACATE", "nombre": "AVOCADO", "estado": "NUEVO LEON", "precio": 69.45, "fecha": "2026-11-10",
             "cambio30dPct": 8.2, "proyeccion30dPct": -3.0, "unidad": "MXN/kg", "desactualizado": False}
        return {**t, **cambios}

    def test_sube_con_proyeccion_y_aclara_que_son_precios_al_consumidor(self):
        n = noticias._noticia_de_precio(self.tendencia(), "2026-11-15")
        self.assertEqual((n["categoria"], n["destino"], n["id"]), ("farm", "mercado", "precio-AGUACATE"))
        self.assertEqual(n["titulo"], "Avocado up 8% in Nuevo Leon over 30 days")
        self.assertIn("69.5 MXN/kg (as of 2026-11-10)", n["resumen"])
        self.assertIn("-3%", n["resumen"])
        self.assertIn("not farm-gate prices", n["resumen"])

    def test_baja_y_sin_proyeccion(self):
        n = noticias._noticia_de_precio(self.tendencia(cambio30dPct=-12.4, proyeccion30dPct=None), "2026-11-15")
        self.assertIn("down 12%", n["titulo"])
        self.assertNotIn("Projected", n["resumen"])

    def test_no_es_noticia_un_cambio_chico_ni_un_dato_viejo(self):
        self.assertIsNone(noticias._noticia_de_precio(self.tendencia(cambio30dPct=4.9), "2026-11-15"))
        self.assertIsNone(noticias._noticia_de_precio(self.tendencia(cambio30dPct=None), "2026-11-15"))
        self.assertIsNone(noticias._noticia_de_precio(self.tendencia(desactualizado=True), "2026-11-15"))

    def test_propias_incluye_los_precios_y_sigue_igual_sin_ellos(self):
        con = noticias.propias([], [], None, "Monterrey", date(2026, 11, 15), None, [self.tendencia()])
        self.assertEqual([n["id"] for n in con], ["precio-AGUACATE"])
        self.assertEqual(noticias.propias([], [], None, "Monterrey", date(2026, 11, 15)), [])


class PruebasEndpoint(ConDatos):
    @classmethod
    def setUpClass(cls):
        if Path(config.DB_PATH).name == "planificador.db":
            raise RuntimeError("Las pruebas apuntan a la base real; define PLANIFICADOR_DB antes de importar app")
        cls._ctx = TestClient(app)
        cls.c = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def test_estados_sugiere_el_de_la_ubicacion_activa(self):
        r = self.c.get("/api/mercado/estados", params={"municipio": "Monterrey, NL", "hoy": "2026-11-15"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["sugerido"], r.json()["desactualizado"]), ("nuevo_leon", True))
        sin = self.c.get("/api/mercado/estados").json()
        self.assertIsNone(sin["sugerido"])

    def test_productos_y_serie(self):
        r = self.c.get("/api/mercado/productos", params={"estado": "nuevo_leon"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual({p["id"] for p in r.json()["productos"]}, {"AGUACATE", "JITOMATE"})
        s = self.c.get("/api/mercado/serie", params={"estado": "nuevo_leon", "productos": "AGUACATE, JITOMATE", "rango": "mes"})
        self.assertEqual(s.status_code, 200, s.text)
        self.assertEqual([p["id"] for p in s.json()["productos"]], ["AGUACATE", "JITOMATE"])
        self.assertEqual(s.json()["rango"], "mes")

    def test_errores_claros(self):
        get = lambda ruta, **p: self.c.get(f"/api/mercado/{ruta}", params=p).status_code  # noqa: E731
        self.assertEqual(get("productos", estado="no_existe"), 404)
        self.assertEqual(get("productos", estado="../x"), 422)  # el patrón de la ruta lo rechaza
        self.assertEqual(get("serie", estado="nuevo_leon", productos="NOEXISTE"), 404)
        self.assertEqual(get("serie", estado="nuevo_leon", productos=" , "), 422)
        self.assertEqual(get("serie", estado="nuevo_leon", productos="AGUACATE", rango="siglo"), 422)

    def test_sin_datos_generados_responde_404_con_la_instruccion(self):
        with patch.object(mercado, "CARPETA", Path(self._carpeta.name) / "no-existe"):
            self.limpiar()
            r = self.c.get("/api/mercado/estados")
        self.assertEqual(r.status_code, 404)
        self.assertIn("exportar_json.py", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
