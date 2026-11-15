"""Pruebas de la API del Planificador.

Se corren desde la carpeta backend (dentro del contenedor):
    docker compose exec backend python -m unittest discover -s tests -v

Usan una base de datos temporal: no tocan backend/data/planificador.db.
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Antes de importar la app: así config.DB_PATH apunta a una base temporal.
_carpeta = tempfile.mkdtemp()
os.environ["PLANIFICADOR_DB"] = str(Path(_carpeta) / "prueba.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

P = "/api/planificador"


class PruebasPlanificador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = TestClient(app)
        cls.c = cls._ctx.__enter__()  # arranca la app: crea la base con la demo

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def setUp(self):
        """Cada prueba trabaja en su propio plan con una parcela de 10 ha."""
        self.plan = self.c.post(f"{P}/planes", json={"nombre": "Prueba"}).json()
        r = self.c.post(f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": "Lote", "hectareas": 10})
        self.parcela = r.json()
        self.maiz = self.cultivo("Maíz amarillo")  # ciclo 125 días
        self.frijol = self.cultivo("Frijol pinto")  # ciclo 100 días

    def tearDown(self):
        self.c.delete(f"{P}/planes/{self.plan['id']}")

    # ---- ayudas ----
    def cultivo(self, nombre):
        return next(x for x in self.c.get(f"{P}/cultivos").json() if x["nombre"] == nombre)

    def siembra(self, cultivo, inicio, fin=None, ha=None, parcela=None):
        cuerpo = {"cultivoId": cultivo["id"], "fechaSiembra": inicio}
        if fin:
            cuerpo["fechaCosecha"] = fin
        if ha is not None:
            cuerpo["hectareas"] = ha
        return self.c.post(f"{P}/parcelas/{(parcela or self.parcela)['id']}/siembras", json=cuerpo)

    # ---- demo y formato ----
    def test_la_demo_se_carga_y_sale_en_camel_case(self):
        planes = self.c.get(f"{P}/planes").json()
        demo = next(p for p in planes if p["nombre"] == "Plan principal")
        plan = self.c.get(f"{P}/planes/{demo['id']}").json()
        self.assertEqual({p["nombre"] for p in plan["parcelas"]}, {"La Esperanza", "El Rancho"})
        siembra = plan["parcelas"][0]["siembras"][0]
        self.assertIn("fechaSiembra", siembra)
        self.assertIn("cicloDias", siembra["cultivo"])
        fechas = [s["fechaSiembra"] for s in plan["parcelas"][0]["siembras"]]
        self.assertEqual(fechas, sorted(fechas))  # ordenadas por fecha

    # ---- siembras ----
    def test_cosecha_y_hectareas_se_calculan_si_no_se_mandan(self):
        r = self.siembra(self.maiz, "2030-01-10")
        self.assertEqual(r.status_code, 201)
        s = r.json()
        self.assertEqual(s["fechaCosecha"], "2030-05-15")  # 10 ene + 125 días
        self.assertEqual(s["hectareas"], 10)  # las de la parcela

    def test_traslape_se_rechaza_con_aviso_y_fecha_libre(self):
        self.assertEqual(self.siembra(self.maiz, "2030-01-10", "2030-05-15").status_code, 201)
        r = self.siembra(self.frijol, "2030-05-01", "2030-08-01")
        self.assertEqual(r.status_code, 409)
        d = r.json()["detail"]
        self.assertIn("Maíz amarillo", d["mensaje"])
        self.assertEqual(d["libreDesde"], "2030-05-16")
        self.assertEqual(d["conflicto"]["fechaCosecha"], "2030-05-15")

    def test_el_dia_de_cosecha_esta_ocupado_y_el_siguiente_esta_libre(self):
        self.siembra(self.maiz, "2030-01-10", "2030-05-15")
        self.assertEqual(self.siembra(self.frijol, "2030-05-15", "2030-08-15").status_code, 409)
        self.assertEqual(self.siembra(self.frijol, "2030-05-16", "2030-08-15").status_code, 201)

    def test_una_siembra_que_envuelve_a_otra_tambien_choca(self):
        self.siembra(self.maiz, "2030-03-01", "2030-04-01")
        self.assertEqual(self.siembra(self.frijol, "2030-01-01", "2030-12-01").status_code, 409)

    def test_parcelas_distintas_si_pueden_coincidir(self):
        otra = self.c.post(
            f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": "Otro lote", "hectareas": 5}
        ).json()
        self.assertEqual(self.siembra(self.maiz, "2030-01-10", "2030-05-15").status_code, 201)
        self.assertEqual(self.siembra(self.maiz, "2030-01-10", "2030-05-15", parcela=otra).status_code, 201)

    def test_datos_invalidos(self):
        self.assertEqual(self.siembra(self.maiz, "2030-05-10", "2030-05-10").status_code, 422)  # mismo día
        self.assertEqual(self.siembra(self.maiz, "2030-05-10", "2030-05-01").status_code, 422)  # al revés
        self.assertEqual(self.siembra(self.maiz, "2030-01-10", ha=11).status_code, 422)  # no cabe
        self.assertEqual(self.siembra(self.maiz, "2030-01-10", ha=0).status_code, 422)
        self.assertEqual(self.siembra({"id": 9999}, "2030-01-10").status_code, 404)  # cultivo inexistente
        r = self.c.post(f"{P}/parcelas/9999/siembras", json={"cultivoId": self.maiz["id"], "fechaSiembra": "2030-01-10"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.siembra(self.maiz, "no-es-fecha").status_code, 422)

    def test_editar_siembra(self):
        a = self.siembra(self.maiz, "2030-01-10", "2030-05-15").json()
        b = self.siembra(self.frijol, "2030-05-16", "2030-08-15").json()
        # Alargar la primera hasta chocar con la segunda
        r = self.c.patch(f"{P}/siembras/{a['id']}", json={"fechaCosecha": "2030-06-01"})
        self.assertEqual(r.status_code, 409)
        # Dejar las mismas fechas no choca consigo misma
        r = self.c.patch(f"{P}/siembras/{a['id']}", json={"fechaCosecha": "2030-05-15"})
        self.assertEqual(r.status_code, 200)
        # Cambiar solo las hectáreas conserva todo lo demás
        r = self.c.patch(f"{P}/siembras/{b['id']}", json={"hectareas": 4})
        self.assertEqual(r.json()["hectareas"], 4)
        self.assertEqual(r.json()["fechaSiembra"], "2030-05-16")
        # Mover la primera lejos sí se puede
        r = self.c.patch(f"{P}/siembras/{a['id']}", json={"fechaSiembra": "2029-01-01", "fechaCosecha": "2029-05-01"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.patch(f"{P}/siembras/9999", json={"hectareas": 1}).status_code, 404)

    def test_borrar_siembra(self):
        s = self.siembra(self.maiz, "2030-01-10").json()
        self.assertEqual(self.c.delete(f"{P}/siembras/{s['id']}").status_code, 204)
        self.assertEqual(self.c.delete(f"{P}/siembras/{s['id']}").status_code, 404)
        self.assertEqual(self.siembra(self.maiz, "2030-01-10").status_code, 201)  # el hueco quedó libre

    # ---- parcelas ----
    def test_nombre_de_parcela_repetido_aunque_cambien_acentos_y_mayusculas(self):
        self.c.post(f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": "Él Rancho", "hectareas": 1})
        r = self.c.post(f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": " EL  RANCHO ", "hectareas": 1})
        self.assertEqual(r.status_code, 409)

    def test_no_se_puede_reducir_la_parcela_debajo_de_una_siembra(self):
        self.siembra(self.maiz, "2030-01-10", ha=8)
        r = self.c.patch(f"{P}/parcelas/{self.parcela['id']}", json={"hectareas": 5})
        self.assertEqual(r.status_code, 409)
        r = self.c.patch(f"{P}/parcelas/{self.parcela['id']}", json={"hectareas": 8})
        self.assertEqual(r.status_code, 200)

    def test_borrar_parcela_borra_sus_siembras(self):
        self.siembra(self.maiz, "2030-01-10")
        self.assertEqual(self.c.delete(f"{P}/parcelas/{self.parcela['id']}").status_code, 204)
        plan = self.c.get(f"{P}/planes/{self.plan['id']}").json()
        self.assertEqual(plan["parcelas"], [])

    # ---- catálogo ----
    def test_buscar_cultivos_sin_importar_acentos(self):
        nombres = [x["nombre"] for x in self.c.get(f"{P}/cultivos", params={"q": "MAIZ"}).json()]
        self.assertEqual(nombres, ["Maíz amarillo"])
        self.assertEqual(self.c.get(f"{P}/cultivos", params={"q": "zzz"}).json(), [])

    def test_crear_cultivo_y_evitar_duplicados(self):
        r = self.c.post(f"{P}/cultivos", json={"nombre": "Chile jalapeño", "tipo": "Hortaliza", "cicloDias": 90})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["tipo"], "hortaliza")
        r = self.c.post(f"{P}/cultivos", json={"nombre": "CHILE JALAPENO", "tipo": "hortaliza", "cicloDias": 90})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["cultivo"]["nombre"], "Chile jalapeño")
        r = self.c.post(f"{P}/cultivos", json={"nombre": "Otro", "tipo": "x", "cicloDias": 0})
        self.assertEqual(r.status_code, 422)

    # ---- planes ----
    def test_planes_crear_renombrar_borrar(self):
        p = self.c.post(f"{P}/planes", json={"nombre": "Plan 2027"}).json()
        r = self.c.patch(f"{P}/planes/{p['id']}", json={"nombre": "Plan 2027 B"})
        self.assertEqual(r.json()["nombre"], "Plan 2027 B")
        self.assertEqual(self.c.delete(f"{P}/planes/{p['id']}").status_code, 204)
        self.assertEqual(self.c.get(f"{P}/planes/{p['id']}").status_code, 404)
        self.assertEqual(self.c.post(f"{P}/planes", json={"nombre": "   "}).status_code, 422)


    # ---- cultivos en curso (Principal) ----
    def activos(self, hoy, **params):
        return self.c.get("/api/principal/cultivos-activos", params={"planId": self.plan["id"], "hoy": hoy, **params})

    def test_activos_dia_etapa_y_avance(self):
        self.siembra(self.maiz, "2030-01-01", "2030-01-10")  # 10 días contando ambos extremos
        primero = self.activos("2030-01-01").json()[0]
        self.assertEqual((primero["dia"], primero["diasTotales"], primero["etapa"], primero["etapas"]), (1, 10, 1, 5))
        medio = self.activos("2030-01-05").json()[0]
        self.assertEqual((medio["dia"], medio["etapa"], medio["avance"]), (5, 3, 50))
        ultimo = self.activos("2030-01-10").json()[0]  # el día de la cosecha todavía está en curso
        self.assertEqual((ultimo["dia"], ultimo["etapa"], ultimo["avance"]), (10, 5, 100))
        self.assertEqual(ultimo["parcela"]["nombre"], "Lote")
        self.assertEqual(ultimo["cultivo"]["nombre"], "Maíz amarillo")

    def test_activos_excluye_pasadas_y_futuras(self):
        self.siembra(self.maiz, "2030-01-01", "2030-01-10")
        self.assertEqual(self.activos("2029-12-31").json(), [])
        self.assertEqual(self.activos("2030-01-11").json(), [])

    def test_activos_ordena_por_la_que_cosecha_primero(self):
        otra = self.c.post(f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": "Otro", "hectareas": 5}).json()
        self.siembra(self.maiz, "2030-01-01", "2030-01-10")
        self.siembra(self.frijol, "2030-01-03", "2030-01-08", parcela=otra)
        nombres = [a["cultivo"]["nombre"] for a in self.activos("2030-01-05").json()]
        self.assertEqual(nombres, ["Frijol pinto", "Maíz amarillo"])

    def test_activos_solo_del_plan_pedido(self):
        self.siembra(self.maiz, "2030-01-01", "2030-01-10")
        otro = self.c.post(f"{P}/planes", json={"nombre": "Otro plan"}).json()
        r = self.c.get("/api/principal/cultivos-activos", params={"planId": otro["id"], "hoy": "2030-01-05"})
        self.assertEqual(r.json(), [])
        self.c.delete(f"{P}/planes/{otro['id']}")

    def test_activos_sin_plan_usa_el_primero_y_plan_inexistente_da_404(self):
        # El primer plan es la demo (maíz y sorgo en curso hoy)
        from app import db

        r = self.c.get("/api/principal/cultivos-activos", params={"hoy": db.hoy().isoformat()})
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual({a["cultivo"]["nombre"] for a in r.json()}, {"Maíz amarillo", "Sorgo"})
        r = self.c.get("/api/principal/cultivos-activos", params={"planId": 99999})
        self.assertEqual(r.status_code, 404)
        self.assertIn("mensaje", r.json()["detail"])

    # ---- resumen del ciclo y recomendaciones ----
    def analisis(self, hoy):
        r = self.c.get(f"{P}/planes/{self.plan['id']}/analisis", params={"hoy": hoy})
        self.assertEqual(r.status_code, 200)
        return r.json()

    def parcela_nueva(self, nombre, ha):
        return self.c.post(f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": nombre, "hectareas": ha}).json()

    def test_resumen_del_ciclo(self):
        otra = self.parcela_nueva("Otro lote", 5)
        self.siembra(self.maiz, "2030-01-01", "2030-01-10", ha=8)  # en curso el día 5
        self.siembra(self.frijol, "2030-02-01", "2030-02-10")  # futura
        self.siembra(self.maiz, "2030-01-03", "2030-01-20", parcela=otra)  # en curso, 5 ha
        r = self.analisis("2030-01-05")["resumen"]
        self.assertEqual((r["totalSiembras"], r["cultivosDistintos"], r["enCurso"]), (3, 2, 2))
        self.assertEqual((r["hectareasTotales"], r["hectareasEnUso"], r["usoSuelo"]), (15, 13, 87))
        self.assertEqual(r["proximaCosecha"]["fecha"], "2030-01-10")
        self.assertEqual(r["proximaCosecha"]["diasRestantes"], 5)
        self.assertEqual((r["proximaCosecha"]["cultivo"], r["proximaCosecha"]["parcela"]), ("Maíz amarillo", "Lote"))

    def test_resumen_de_un_plan_sin_siembras(self):
        r = self.analisis("2030-01-05")["resumen"]
        self.assertEqual((r["totalSiembras"], r["enCurso"], r["usoSuelo"]), (0, 0, 0))
        self.assertIsNone(r["proximaCosecha"])
        vacio = self.c.post(f"{P}/planes", json={"nombre": "Sin parcelas"}).json()
        r = self.c.get(f"{P}/planes/{vacio['id']}/analisis", params={"hoy": "2030-01-05"}).json()["resumen"]
        self.assertEqual((r["hectareasTotales"], r["usoSuelo"]), (0, 0))  # sin dividir entre cero
        self.c.delete(f"{P}/planes/{vacio['id']}")

    def test_despues_de_un_cereal_se_sugiere_una_leguminosa(self):
        self.siembra(self.maiz, "2030-01-10")  # cosecha el 2030-05-15
        recs = self.analisis("2030-01-01")["recomendaciones"]
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["parcela"]["nombre"], "Lote")
        self.assertEqual(r["despuesDe"]["cultivo"]["nombre"], "Maíz amarillo")
        self.assertEqual(r["sugerido"]["nombre"], "Frijol pinto")
        self.assertEqual(r["desde"], "2030-05-16")  # el día siguiente a la cosecha
        self.assertIn("nitrógeno", r["razon"])
        self.assertNotIn("afinidad", str(r).lower())  # sin porcentajes inventados

    def test_despues_de_una_leguminosa_se_sugiere_un_cereal_distinto_al_ultimo(self):
        self.siembra(self.frijol, "2030-01-10")
        r = self.analisis("2030-01-01")["recomendaciones"][0]
        self.assertEqual(r["sugerido"]["tipo"], "cereal")
        self.assertEqual(r["sugerido"]["nombre"], "Maíz amarillo")  # empate: el primero por nombre

    def test_se_prefiere_variar_y_nunca_repetir_el_ultimo(self):
        self.c.post(f"{P}/cultivos", json={"nombre": "Haba", "tipo": "leguminosa", "cicloDias": 120})  # 409 si ya existe
        self.siembra(self.frijol, "2030-01-01", "2030-04-10")
        self.siembra(self.maiz, "2030-04-11", "2030-08-15")
        r = self.analisis("2030-01-01")["recomendaciones"][0]
        # El frijol ya se sembró en esta parcela y la haba no: se propone la haba
        self.assertEqual(r["sugerido"]["nombre"], "Haba")
        # Y tras un cultivo nunca se propone el mismo
        self.siembra(self.frijol, "2030-08-16", "2030-12-01")
        r = self.analisis("2030-01-01")["recomendaciones"][0]
        self.assertNotEqual(r["sugerido"]["nombre"], "Frijol pinto")

    def test_sin_recomendacion_para_frutales_ni_parcelas_vacias(self):
        aguacate = self.cultivo("Aguacate Hass")
        otra = self.parcela_nueva("Huerta", 3)
        self.siembra(aguacate, "2030-01-01", "2030-12-31", parcela=otra)
        # "Lote" no tiene siembras y "Huerta" tiene un frutal: ninguna recibe sugerencia
        self.assertEqual(self.analisis("2030-01-01")["recomendaciones"], [])

    def test_la_fecha_sugerida_no_queda_en_el_pasado(self):
        self.siembra(self.maiz, "2030-01-10", "2030-05-15")
        r = self.analisis("2031-01-01")["recomendaciones"][0]
        self.assertEqual(r["desde"], "2031-01-01")

    def test_analisis_de_un_plan_inexistente_da_404(self):
        self.assertEqual(self.c.get(f"{P}/planes/99999/analisis").status_code, 404)


class PruebasUbicaciones(unittest.TestCase):
    """Lugares para el clima: listar, agregar, "Mi ubicación", borrar, búsqueda y suelo."""

    @classmethod
    def setUpClass(cls):
        cls._ctx = TestClient(app)
        cls.c = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    U = "/api/ubicaciones"
    GDL = {"nombre": "Guadalajara, Jalisco, México", "lat": 20.67, "lon": -103.35, "zona": "America/Mexico_City"}

    def test_las_cuatro_ciudades_de_inicio(self):
        nombres = [u["nombre"] for u in self.c.get(self.U).json()]
        for n in ("Monterrey, NL", "Saltillo, COAH", "Culiacán, SIN", "Mérida, YUC"):
            self.assertIn(n, nombres)

    def test_agregar_y_quitar_un_lugar(self):
        r = self.c.post(self.U, json=self.GDL)
        self.assertEqual(r.status_code, 201)
        nuevo = r.json()
        self.assertEqual(nuevo["nombre"], self.GDL["nombre"])
        # No se puede repetir, aunque cambien acentos, mayúsculas o espacios
        r = self.c.post(self.U, json={**self.GDL, "nombre": "  GUADALAJARA,  jalisco, MEXICO "})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.c.delete(f"{self.U}/{nuevo['id']}").status_code, 204)
        self.assertEqual(self.c.delete(f"{self.U}/{nuevo['id']}").status_code, 404)

    def test_datos_invalidos(self):
        r = self.c.post(self.U, json={**self.GDL, "zona": "Marte/Olimpo"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("zona horaria", r.json()["detail"]["mensaje"])
        self.assertEqual(self.c.post(self.U, json={**self.GDL, "lat": 95}).status_code, 422)  # fuera de rango
        self.assertEqual(self.c.post(self.U, json={**self.GDL, "nombre": "   "}).status_code, 422)

    def test_mi_ubicacion_se_actualiza_y_es_una_sola(self):
        a = self.c.put(f"{self.U}/mi-ubicacion", json={"lat": 25.5, "lon": -100.1, "zona": "America/Monterrey"}).json()
        b = self.c.put(f"{self.U}/mi-ubicacion", json={"lat": 26.0, "lon": -101.0, "zona": "America/Monterrey"}).json()
        self.assertEqual((a["nombre"], a["id"]), ("Mi ubicación", b["id"]))
        self.assertEqual((b["lat"], b["lon"]), (26.0, -101.0))
        self.assertEqual(sum(u["nombre"] == "Mi ubicación" for u in self.c.get(self.U).json()), 1)
        self.c.delete(f"{self.U}/{b['id']}")

    def test_no_se_puede_borrar_la_ultima_ubicacion(self):
        from app import db
        from app.services import ubicaciones as servicio

        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript(db.MIGRACION_UBICACIONES)
        con.execute("INSERT INTO ubicacion (nombre, clave, lat, lon, zona) VALUES ('Única', 'unica', 1, 1, 'UTC')")
        with self.assertRaises(servicio.Conflicto):
            servicio.borrar(con, 1)

    def test_buscar_lugares_usa_el_geocodificador_sin_red(self):
        from app.services import ubicaciones as servicio

        candidatos = [dict(self.GDL)]
        with patch.object(servicio, "geocodificar", new=AsyncMock(return_value=candidatos)):
            r = self.c.get(f"{self.U}/buscar", params={"q": "Guadalajara"})
        self.assertEqual((r.status_code, r.json()), (200, candidatos))
        with patch.object(servicio, "geocodificar", new=AsyncMock(side_effect=servicio.ErrorBusqueda("sin servicio"))):
            self.assertEqual(self.c.get(f"{self.U}/buscar", params={"q": "Guadalajara"}).status_code, 502)
        # Una búsqueda de menos de 2 letras se rechaza sin llamar al servicio externo
        r = self.c.get(f"{self.U}/buscar", params={"q": "a"})
        self.assertEqual(r.status_code, 422)

    def test_la_busqueda_se_limita_a_mexico(self):
        from app.services import ubicaciones as servicio

        class Respuesta:
            def raise_for_status(self):
                pass

            def json(self):
                return {"results": [
                    {"name": "Hermosillo", "admin1": "Sonora", "country": "México", "country_code": "MX",
                     "latitude": 29.07, "longitude": -110.95, "timezone": "America/Hermosillo"},
                    {"name": "Benito Juárez", "admin1": "Buenos Aires", "country": "Argentina", "country_code": "AR",
                     "latitude": -37.67, "longitude": -59.81, "timezone": "America/Argentina/Buenos_Aires"},
                ]}

        pedido = AsyncMock(return_value=Respuesta())
        with patch("httpx.AsyncClient.get", new=pedido):
            candidatos = asyncio.run(servicio.geocodificar("Hermosillo"))
        self.assertEqual(pedido.await_args.kwargs["params"]["countryCode"], "MX")  # se pide solo México
        self.assertEqual([c["nombre"] for c in candidatos], ["Hermosillo, Sonora, México"])  # y se descarta lo demás

    def test_el_clima_busca_la_ubicacion_sin_importar_acentos_ni_mayusculas(self):
        from app import db
        from app.services import ubicaciones as servicio

        con = db.conectar()
        self.assertEqual(servicio.buscar(con, "culiacan, sin").nombre, "Culiacán, SIN")
        self.assertIsNone(servicio.buscar(con, "Narnia"))
        self.assertEqual(self.c.get("/api/principal/clima", params={"municipio": "Narnia"}).status_code, 404)

    def test_migracion_de_una_base_antigua_conserva_los_datos(self):
        from app import config, db

        ruta = Path(tempfile.mkdtemp()) / "antigua.db"
        con = sqlite3.connect(ruta)
        con.executescript(db.ESQUEMA)  # una base como la de la versión 1: sin tabla de ubicaciones
        con.execute("INSERT INTO plan (nombre) VALUES ('Plan de antes')")
        con.execute("PRAGMA user_version = 1")
        con.commit()
        con.close()
        with patch.object(config, "DB_PATH", ruta):
            db.iniciar()
            db.iniciar()  # una segunda vez no debe duplicar nada
            con = db.conectar()
            self.assertEqual(con.execute("SELECT COUNT(*) FROM ubicacion").fetchone()[0], 4)
            self.assertEqual(con.execute("SELECT nombre FROM plan").fetchone()[0], "Plan de antes")
            self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 2)
            con.close()

    def test_suelo_busca_puntos_cercanos_solo_en_lugares_sin_punto_de_campo(self):
        from app.services import soilgrids
        from app.services.ubicaciones import Ubicacion

        con_campo = Ubicacion(1, "Con campo", 10.0, 10.0, "UTC", 10.5, 10.5)
        sin_campo = Ubicacion(2, "Sin campo", 11.0, 11.0, "UTC")
        self.assertEqual(soilgrids._puntos(con_campo), [(10.5, 10.5)])
        self.assertEqual(soilgrids._puntos(sin_campo)[0], (11.0, 11.0))
        self.assertEqual(len(soilgrids._puntos(sin_campo)), 9)

        # Los dos primeros puntos no tienen dato (centro urbano): usa el tercero y ya no sigue
        nuevo = Ubicacion(3, "Ciudad nueva", 31.111, 41.111, "UTC")
        mock = AsyncMock(side_effect=[None, None, 7.4])
        with patch.object(soilgrids, "_consultar_punto", new=mock):
            self.assertEqual(asyncio.run(soilgrids.ph(nuevo)), 7.4)
        self.assertEqual(mock.await_count, 3)
        # La segunda vez sale de la caché: no consulta
        with patch.object(soilgrids, "_consultar_punto", new=mock):
            self.assertEqual(asyncio.run(soilgrids.ph(nuevo)), 7.4)
        self.assertEqual(mock.await_count, 3)


if __name__ == "__main__":
    unittest.main()
