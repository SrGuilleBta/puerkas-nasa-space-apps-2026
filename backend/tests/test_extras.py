"""Pruebas de costos e ingresos, tareas, copiar y exportar el plan, y el estado de las ubicaciones."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Antes de importar la app: así config.DB_PATH apunta a una base temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

import sqlite3  # noqa: E402

from app import config, db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import catalogo_cultivos, estados  # noqa: E402

P = "/api/planificador"


class PruebasExtras(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if Path(config.DB_PATH).name == "planificador.db":
            raise RuntimeError("Las pruebas apuntan a la base real; define PLANIFICADOR_DB antes de importar app")
        cls._ctx = TestClient(app)
        cls.c = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def setUp(self):
        self.plan = self.c.post(f"{P}/planes", json={"nombre": "Prueba extras"}).json()
        self.parcela = self.c.post(
            f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": "Lote", "hectareas": 10}
        ).json()
        self.maiz = next(x for x in self.c.get(f"{P}/cultivos").json() if x["nombre"] == "Maíz grano")
        self.creados = [self.plan["id"]]

    def tearDown(self):
        for id_ in self.creados:
            self.c.delete(f"{P}/planes/{id_}")

    def siembra(self, inicio="2030-01-10", fin="2030-05-10", ha=4, **extra):
        r = self.c.post(
            f"{P}/parcelas/{self.parcela['id']}/siembras",
            json={"cultivoId": self.maiz["id"], "fechaSiembra": inicio, "fechaCosecha": fin, "hectareas": ha, **extra},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def analisis(self, hoy="2030-01-01", plan=None):
        return self.c.get(f"{P}/planes/{(plan or self.plan)['id']}/analisis", params={"hoy": hoy}).json()

    # ---------------- costos e ingresos ----------------
    def test_economia_se_calcula_con_los_datos_capturados(self):
        s = self.siembra(rendimientoTHa=3, precioT=5000, costoHa=7000)  # 4 ha
        self.assertEqual(s["ingresoEstimado"], 60000)  # 3 t/ha x 5,000 $/t x 4 ha
        self.assertEqual(s["costoTotal"], 28000)
        self.assertEqual(s["gananciaEstimada"], 32000)

    def test_sin_todos_los_datos_solo_salen_las_cifras_posibles(self):
        s = self.siembra(costoHa=7000)
        self.assertEqual((s["ingresoEstimado"], s["costoTotal"], s["gananciaEstimada"]), (None, 28000, None))
        s2 = self.c.patch(f"{P}/siembras/{s['id']}", json={"rendimientoTHa": 2, "precioT": 5000}).json()
        self.assertEqual((s2["ingresoEstimado"], s2["gananciaEstimada"]), (40000, 12000))
        self.assertEqual(s2["costoHa"], 7000)  # lo que no se mandó se conserva

    def test_se_puede_borrar_un_dato_economico_con_null(self):
        s = self.siembra(rendimientoTHa=3, precioT=5000, costoHa=7000)
        s2 = self.c.patch(f"{P}/siembras/{s['id']}", json={"costoHa": None}).json()
        self.assertIsNone(s2["costoHa"])
        self.assertEqual(s2["ingresoEstimado"], 60000)

    def test_rechaza_datos_economicos_negativos(self):
        r = self.c.post(f"{P}/parcelas/{self.parcela['id']}/siembras",
                        json={"cultivoId": self.maiz["id"], "fechaSiembra": "2030-01-10", "precioT": -1})
        self.assertEqual(r.status_code, 422)

    def test_resumen_suma_la_economia_del_plan(self):
        self.siembra("2030-01-10", "2030-02-10", ha=4, rendimientoTHa=3, precioT=5000, costoHa=7000)
        self.siembra("2030-03-01", "2030-04-01", ha=2, costoHa=1000)  # solo costo
        r = self.analisis()["resumen"]
        self.assertEqual(r["inversionEstimada"], 30000)  # 28,000 + 2,000
        self.assertEqual(r["ingresoEstimado"], 60000)
        self.assertEqual(r["gananciaEstimada"], 32000)  # solo cuenta la siembra con ingreso y costo
        self.assertEqual(r["siembrasConEconomia"], 2)

    def test_resumen_sin_datos_economicos(self):
        self.siembra()
        r = self.analisis()["resumen"]
        self.assertEqual((r["inversionEstimada"], r["ingresoEstimado"], r["siembrasConEconomia"]), (None, None, 0))

    # ---------------- tareas ----------------
    def test_crear_listar_editar_y_borrar_tareas(self):
        s = self.siembra()
        t = self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "Spread fertilizer", "tipo": "fertilize", "fecha": "2030-02-01"})
        self.assertEqual(t.status_code, 201, t.text)
        t = t.json()
        self.assertFalse(t["hecha"])
        hecha = self.c.patch(f"{P}/tareas/{t['id']}", json={"hecha": True}).json()
        self.assertTrue(hecha["hecha"])
        self.assertEqual(hecha["titulo"], "Spread fertilizer")  # lo demás no cambia
        self.assertEqual(len(self.c.get(f"{P}/siembras/{s['id']}/tareas").json()), 1)
        self.assertEqual(self.c.delete(f"{P}/tareas/{t['id']}").status_code, 204)
        self.assertEqual(self.c.get(f"{P}/siembras/{s['id']}/tareas").json(), [])

    def test_las_tareas_salen_ordenadas_por_fecha(self):
        s = self.siembra()
        for titulo, fecha in [("B", "2030-03-01"), ("A", "2030-02-01")]:
            self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": titulo, "fecha": fecha})
        self.assertEqual([t["titulo"] for t in self.c.get(f"{P}/siembras/{s['id']}/tareas").json()], ["A", "B"])

    def test_tarea_con_tipo_o_titulo_invalido(self):
        s = self.siembra()
        mala = self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "X", "tipo": "volar", "fecha": "2030-02-01"})
        self.assertEqual(mala.status_code, 422)
        vacia = self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "   ", "fecha": "2030-02-01"})
        self.assertEqual(vacia.status_code, 422)
        self.assertEqual(self.c.get(f"{P}/siembras/9999/tareas").status_code, 404)

    def test_calendario_sugerido_reparte_las_tareas_en_el_ciclo(self):
        s = self.siembra("2030-01-01", "2030-05-11")  # 130 días
        r = self.c.post(f"{P}/siembras/{s['id']}/tareas/sugeridas")
        self.assertEqual(r.status_code, 201, r.text)
        tareas = r.json()
        self.assertEqual(tareas[0]["tipo"], "plant")
        self.assertEqual(tareas[0]["fecha"], "2030-01-01")
        self.assertEqual(tareas[-1]["tipo"], "harvest")
        self.assertEqual(tareas[-1]["fecha"], "2030-05-11")
        self.assertEqual([t["fecha"] for t in tareas], sorted(t["fecha"] for t in tareas))

    def test_calendario_sugerido_no_duplica(self):
        s = self.siembra()
        self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "Mine", "fecha": "2030-02-01"})
        self.assertEqual(self.c.post(f"{P}/siembras/{s['id']}/tareas/sugeridas").status_code, 409)

    def test_borrar_la_siembra_borra_sus_tareas(self):
        s = self.siembra()
        t = self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "X", "fecha": "2030-02-01"}).json()
        self.c.delete(f"{P}/siembras/{s['id']}")
        self.assertEqual(self.c.patch(f"{P}/tareas/{t['id']}", json={"hecha": True}).status_code, 404)

    def test_el_resumen_cuenta_tareas_pendientes_y_vencidas(self):
        s = self.siembra()
        a = self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "Vieja", "fecha": "2030-01-15"}).json()
        self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "Futura", "fecha": "2030-03-01"})
        self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": "Hecha", "fecha": "2030-01-05"})
        hecha = self.c.get(f"{P}/siembras/{s['id']}/tareas").json()
        self.c.patch(f"{P}/tareas/{next(t['id'] for t in hecha if t['titulo'] == 'Hecha')}", json={"hecha": True})
        r = self.analisis(hoy="2030-02-01")["resumen"]
        self.assertEqual((r["tareasPendientes"], r["tareasVencidas"]), (2, 1))
        self.assertEqual(a["fecha"], "2030-01-15")

    def test_tareas_vencidas_para_principal(self):
        s = self.siembra()
        url = f"{P.replace('planificador', 'principal')}/tareas-vencidas"
        for titulo, fecha in [("Vieja", "2030-01-15"), ("Mas vieja", "2030-01-12"), ("Futura", "2030-03-01"), ("Hecha", "2030-01-05")]:
            self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": titulo, "fecha": fecha})
        hecha = next(t for t in self.c.get(f"{P}/siembras/{s['id']}/tareas").json() if t["titulo"] == "Hecha")
        self.c.patch(f"{P}/tareas/{hecha['id']}", json={"hecha": True})

        r = self.c.get(url, params={"planId": self.plan["id"], "hoy": "2030-02-01"})
        self.assertEqual(r.status_code, 200, r.text)
        datos = r.json()
        self.assertEqual(datos["total"], 2)  # no cuenta la hecha ni la futura
        self.assertEqual([t["titulo"] for t in datos["tareas"]], ["Mas vieja", "Vieja"])  # la más atrasada primero
        primera = datos["tareas"][0]
        self.assertEqual((primera["diasRetraso"], primera["cultivo"], primera["parcela"]), (20, "Maíz grano", "Lote"))

        # El mismo día de la fecha de la tarea todavía no cuenta como vencida
        self.assertEqual(self.c.get(url, params={"planId": self.plan["id"], "hoy": "2030-01-12"}).json()["total"], 0)
        self.assertEqual(self.c.get(url, params={"planId": 999999, "hoy": "2030-02-01"}).status_code, 404)

    def test_tareas_vencidas_limita_la_lista_pero_cuenta_todas(self):
        s = self.siembra()
        for i in range(7):
            self.c.post(f"{P}/siembras/{s['id']}/tareas", json={"titulo": f"T{i}", "fecha": f"2030-01-{11 + i:02d}"})
        datos = self.c.get(f"{P.replace('planificador', 'principal')}/tareas-vencidas", params={"planId": self.plan["id"], "hoy": "2030-02-01"}).json()
        self.assertEqual((datos["total"], len(datos["tareas"])), (7, 5))

    # ---------------- precio y rendimiento (SIAP) en cultivos activos ----------------
    IND = {
        "precio": {"pmr_real_ultimo": 5500, "pmr_real_p50": 5000, "unidad": "$/t"},
        "rendimiento": {"p50": 3.8, "unidad": "t/ha"},
        "anio_ultimo": 2025,
        "rentabilidad": {"nivel": "alta"},
        "sensibilidad_sequia": "alta",
        "riesgo_hidrico": {"nivel": "alto"},
    }

    def test_mercado_resume_siap_y_compara_el_precio_con_su_mediana(self):
        servicio = catalogo_cultivos.catalogo_servicio
        with patch.object(servicio, "indicadores_de", return_value=(self.IND, {"nombre": "Nuevo León"})) as m:
            r = catalogo_cultivos.mercado("maiz-grano", "19")
        m.assert_called_once_with("maiz-grano", ["19", "00"])  # primero el estado, luego el país
        self.assertEqual((r["precio"], r["variacion_pct"], r["rendimiento"], r["anio"]), (5500, 10, 3.8, 2025))
        self.assertEqual(r["fuente"], "SIAP · Nuevo León")
        self.assertEqual(
            [e["texto"] for e in r["etiquetas"]], ["High profitability", "Drought sensitive", "High water risk"]
        )
        self.assertEqual([e["tipo"] for e in r["etiquetas"]], ["positiva", "negativa", "negativa"])

    def test_mercado_sin_estado_usa_los_datos_nacionales_y_no_inventa(self):
        servicio = catalogo_cultivos.catalogo_servicio
        with patch.object(servicio, "indicadores_de", return_value=(self.IND, {"nombre": "México"})) as m:
            self.assertEqual(catalogo_cultivos.mercado("maiz-grano", None)["fuente"], "SIAP · México")
        m.assert_called_once_with("maiz-grano", ["00"])
        self.assertIsNone(catalogo_cultivos.mercado(None, "19"))  # cultivo que no es del catálogo
        with patch.object(servicio, "indicadores_de", return_value=(None, None)):
            self.assertIsNone(catalogo_cultivos.mercado("maiz-grano", "19"))
        with patch.object(servicio, "indicadores_de", side_effect=servicio.SinDatos("falta")):
            self.assertIsNone(catalogo_cultivos.mercado("maiz-grano", "19"))  # la pipeline no se ha corrido

    def test_cultivos_activos_incluye_el_mercado_del_estado_de_la_ubicacion(self):
        self.siembra("2030-01-10", "2030-05-10")
        falso = {
            "precio": 5500.0, "precio_unidad": "$/t", "variacion_pct": 10, "rendimiento": 3.8,
            "rendimiento_unidad": "t/ha", "anio": 2025, "fuente": "SIAP · Nuevo León",
            "etiquetas": [{"tipo": "positiva", "texto": "High profitability"}],
        }
        with patch.object(catalogo_cultivos, "mercado", return_value=falso) as m:
            r = self.c.get(
                "/api/principal/cultivos-activos",
                params={"planId": self.plan["id"], "hoy": "2030-02-01", "municipio": "Monterrey, NL"},
            )
        self.assertEqual(r.status_code, 200, r.text)
        m.assert_called_once()
        self.assertEqual(m.call_args.args[1], "19")  # Monterrey está en Nuevo León
        mercado = r.json()[0]["mercado"]
        self.assertEqual((mercado["precio"], mercado["variacionPct"], mercado["precioUnidad"]), (5500.0, 10, "$/t"))
        self.assertEqual(mercado["etiquetas"], [{"tipo": "positiva", "texto": "High profitability"}])

    def test_cultivos_activos_sin_datos_de_mercado_sigue_funcionando(self):
        self.siembra("2030-01-10", "2030-05-10")
        with patch.object(catalogo_cultivos, "mercado", return_value=None):
            r = self.c.get("/api/principal/cultivos-activos", params={"planId": self.plan["id"], "hoy": "2030-02-01"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(r.json()[0]["mercado"])

    # ---------------- textura de suelo (EcoCrop) en la ficha ----------------
    def test_textura_de_ecocrop_lee_clases_y_no_inventa(self):
        from app.services import ecocrop

        tabla = {
            "Phaseolus vulgaris": {"optima": ["medium", "organic"], "tolerada": ["heavy", "medium", "light"]},
            "Zea mays": {"optima": [], "tolerada": []},  # EcoCrop no trae su textura
        }
        with patch.object(ecocrop, "_tabla", return_value=tabla):
            self.assertEqual(ecocrop.textura("Phaseolus vulgaris")["optima"], ["medium", "organic"])
            self.assertIsNone(ecocrop.textura("Zea mays"))
            self.assertIsNone(ecocrop.textura("Cultivo inexistente"))
            self.assertIsNone(ecocrop.textura(None))
        self.assertEqual(ecocrop._clases("heavy, medium, rara, "), ["heavy", "medium"])  # ignora lo desconocido
        self.assertEqual(ecocrop._clases(None), [])

    def test_la_ficha_incluye_la_textura_ideal(self):
        datos = catalogo_cultivos._catalogo()["por_id"]
        if "frijol" not in datos:
            self.skipTest("El catálogo de Cultivos no está generado en este equipo")
        ficha = catalogo_cultivos.ficha_por_catalogo("frijol")
        self.assertIn("texturaIdeal", ficha)  # puede ser None si EcoCrop no trae el dato

    # ---------------- copiar y exportar ----------------
    def test_duplicar_mueve_las_fechas_y_conserva_la_economia(self):
        self.siembra("2030-01-10", "2030-05-10", ha=4, rendimientoTHa=3, precioT=5000, costoHa=7000)
        r = self.c.post(f"{P}/planes/{self.plan['id']}/duplicar", json={"nombre": "Plan 2031", "anios": 1})
        self.assertEqual(r.status_code, 201, r.text)
        nuevo = r.json()
        self.creados.append(nuevo["id"])
        self.assertEqual(nuevo["nombre"], "Plan 2031")
        copia = self.c.get(f"{P}/planes/{nuevo['id']}").json()
        s = copia["parcelas"][0]["siembras"][0]
        self.assertEqual((s["fechaSiembra"], s["fechaCosecha"]), ("2031-01-10", "2031-05-10"))
        self.assertEqual((s["hectareas"], s["precioT"], s["gananciaEstimada"]), (4, 5000, 32000))
        self.assertEqual(copia["parcelas"][0]["nombre"], "Lote")
        original = self.c.get(f"{P}/planes/{self.plan['id']}").json()["parcelas"][0]["siembras"][0]
        self.assertEqual(original["fechaSiembra"], "2030-01-10")  # el original no cambia

    def test_duplicar_con_nombre_por_defecto_y_cero_anios(self):
        self.siembra()
        nuevo = self.c.post(f"{P}/planes/{self.plan['id']}/duplicar", json={"anios": 0}).json()
        self.creados.append(nuevo["id"])
        self.assertEqual(nuevo["nombre"], "Prueba extras (copy)")
        s = self.c.get(f"{P}/planes/{nuevo['id']}").json()["parcelas"][0]["siembras"][0]
        self.assertEqual(s["fechaSiembra"], "2030-01-10")

    def test_duplicar_el_29_de_febrero(self):
        self.siembra("2028-02-29", "2028-06-01")
        nuevo = self.c.post(f"{P}/planes/{self.plan['id']}/duplicar", json={"anios": 1}).json()
        self.creados.append(nuevo["id"])
        s = self.c.get(f"{P}/planes/{nuevo['id']}").json()["parcelas"][0]["siembras"][0]
        self.assertEqual(s["fechaSiembra"], "2029-02-28")

    def test_duplicar_valida_los_anios_y_el_plan(self):
        self.assertEqual(self.c.post(f"{P}/planes/{self.plan['id']}/duplicar", json={"anios": 11}).status_code, 422)
        self.assertEqual(self.c.post(f"{P}/planes/9999/duplicar", json={"anios": 1}).status_code, 404)

    def test_exportar_csv(self):
        self.c.patch(f"{P}/parcelas/{self.parcela['id']}", json={"nombre": "=HYPERLINK(1)"})  # un nombre malicioso
        self.siembra(rendimientoTHa=3, precioT=5000, costoHa=7000)
        r = self.c.get(f"{P}/planes/{self.plan['id']}/exportar")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers["content-type"])
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertIn(".csv", r.headers["content-disposition"])
        texto = r.content.decode("utf-8")
        self.assertTrue(texto.startswith("﻿Plot,Plot hectares,Crop"))
        self.assertIn("2030-01-10,2030-05-10,4.0,3.0,5000.0,7000.0,60000.0,28000.0,32000.0", texto)
        self.assertNotIn("\n=HYPERLINK", texto)  # no queda como fórmula
        self.assertIn("'=HYPERLINK(1)", texto)

    def test_exportar_pdf(self):
        # Un nombre con acentos y con caracteres que las fuentes del PDF no cubren: no debe fallar
        self.c.patch(f"{P}/parcelas/{self.parcela['id']}", json={"nombre": "Lote ñandú 中文"})
        self.siembra(rendimientoTHa=3, precioT=5000, costoHa=7000)
        r = self.c.get(f"{P}/planes/{self.plan['id']}/exportar-pdf", params={"hoy": "2030-02-01"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertIn(".pdf", r.headers["content-disposition"])
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertGreater(len(r.content), 1500)

    def test_exportar_pdf_de_plan_vacio_o_inexistente(self):
        r = self.c.get(f"{P}/planes/{self.plan['id']}/exportar-pdf")  # la parcela no tiene siembras
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertEqual(self.c.get(f"{P}/planes/999999/exportar-pdf").status_code, 404)

    def test_exportar_pdf_de_un_plan_grande_pasa_a_otra_pagina(self):
        for i in range(22):
            parcela = self.c.post(
                f"{P}/planes/{self.plan['id']}/parcelas", json={"nombre": f"Parcela {i}", "hectareas": 2}
            ).json()
            self.c.post(
                f"{P}/parcelas/{parcela['id']}/siembras",
                json={"cultivoId": self.maiz["id"], "fechaSiembra": "2030-01-10", "fechaCosecha": "2030-05-10"},
            )
        r = self.c.get(f"{P}/planes/{self.plan['id']}/exportar-pdf", params={"hoy": "2030-02-01"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertGreater(r.content.count(b"/Type /Page\n") + r.content.count(b"/Type /Page "), 2)  # varias páginas

    # ---------------- estado de la ubicación ----------------
    def test_las_ciudades_de_inicio_traen_su_estado(self):
        por_nombre = {u["nombre"]: u["cveEnt"] for u in self.c.get("/api/ubicaciones").json()}
        self.assertEqual(por_nombre["Monterrey, NL"], "19")
        self.assertEqual(por_nombre["Mérida, YUC"], "31")

    def test_lista_de_estados(self):
        lista = self.c.get("/api/ubicaciones/estados").json()
        self.assertEqual(len(lista), 32)
        self.assertIn({"clave": "19", "nombre": "Nuevo León"}, lista)

    def test_se_puede_fijar_y_borrar_el_estado_de_una_ubicacion(self):
        mia = self.c.put("/api/ubicaciones/mi-ubicacion", json={"lat": 20.0, "lon": -100.0, "zona": "America/Mexico_City"}).json()
        self.assertIsNone(mia["cveEnt"])
        fijada = self.c.patch(f"/api/ubicaciones/{mia['id']}", json={"cveEnt": "11"}).json()
        self.assertEqual(fijada["cveEnt"], "11")
        # un cambio pequeño de coordenadas (el GPS se mueve unos metros) conserva el estado
        igual = self.c.put("/api/ubicaciones/mi-ubicacion", json={"lat": 20.01, "lon": -100.01, "zona": "America/Mexico_City"}).json()
        self.assertEqual(igual["cveEnt"], "11")
        # si cambia de lugar (más de 0.5 grados) ya no se sabe
        lejos = self.c.put("/api/ubicaciones/mi-ubicacion", json={"lat": 25.7, "lon": -100.3, "zona": "America/Monterrey"}).json()
        self.assertIsNone(lejos["cveEnt"])
        self.assertEqual(self.c.patch(f"/api/ubicaciones/{mia['id']}", json={"cveEnt": "99"}).status_code, 422)
        self.assertEqual(self.c.patch("/api/ubicaciones/9999", json={"cveEnt": "11"}).status_code, 404)

    def test_agregar_una_ubicacion_con_estado(self):
        r = self.c.post("/api/ubicaciones", json={"nombre": "Guadalajara, Jalisco, Mexico", "lat": 20.67, "lon": -103.35,
                                                  "zona": "America/Mexico_City", "cveEnt": "14"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["cveEnt"], "14")
        self.c.delete(f"/api/ubicaciones/{r.json()['id']}")

    def test_reconoce_el_estado_por_su_nombre(self):
        for nombre, esperado in [("Nuevo León", "19"), ("Coahuila de Zaragoza", "05"), ("State of Mexico", "15"),
                                 ("Mexico City", "09"), ("Michoacán de Ocampo", "16"), ("Jalisco", "14"),
                                 ("Veracruz de Ignacio de la Llave", "30"), ("México", "15")]:
            self.assertEqual(estados.estado_de(nombre), esperado, nombre)
        self.assertIsNone(estados.estado_de("Texas"))
        self.assertIsNone(estados.estado_de(None))

    # ---------------- ficha con manejo y estimaciones ----------------
    def test_estimaciones_de_costos_salen_de_inifap_y_de_la_mediana_nacional(self):
        datos = {"unidad": "Tonelada", "nacional": {"rend_p50": 3.8, "pmr_real_p50": 5400}}
        manejo = {"estado": "Nuevo León", "fichas": [{"costos": [
            {"modalidad": "temporal", "costoTotalHa": 7310, "rendimiento": 3060, "unidadRendimiento": "kg/ha", "precio": 5.1},
            {"modalidad": "temporal", "costoTotalHa": None, "rendimiento": 1, "unidadRendimiento": "kg/ha", "precio": 1},
            {"modalidad": "riego", "costoTotalHa": 29105, "rendimiento": 5000, "unidadRendimiento": "kg/ha", "precio": None},
        ]}]}
        e = catalogo_cultivos.estimaciones_economia(datos, manejo)
        self.assertEqual(len(e), 3)  # la fila sin costo se descarta
        self.assertEqual((e[0]["rendimientoTHa"], e[0]["precioT"], e[0]["costoHa"]), (3.06, 5100, 7310))
        self.assertEqual((e[1]["rendimientoTHa"], e[1]["precioT"]), (5.0, None))
        self.assertEqual(e[2]["fuente"], "SIAP national median")

    def test_sin_estado_la_ficha_pide_elegirlo(self):
        with patch.object(catalogo_cultivos, "_catalogo", lambda: {"cultivos": [], "por_id": {
                "x": {"id": "x", "nombre": "X", "unidad": "Gruesa"}}}):
            f = catalogo_cultivos.ficha_por_catalogo("x", None)
        self.assertTrue(f["manejo"]["necesitaEstado"])
        self.assertEqual(f["estimaciones"], [])  # no es en toneladas: sin mediana nacional

    # ---------------- migración 5 ----------------
    def test_migracion_v5_agrega_economia_tareas_y_estado_sin_perder_datos(self):
        ruta = Path(tempfile.mkdtemp()) / "v4.db"
        con = sqlite3.connect(ruta)
        con.executescript(db.ESQUEMA + db.MIGRACION_UBICACIONES)
        con.execute("ALTER TABLE cultivo ADD COLUMN catalogo_id TEXT")  # como la deja la migración 4
        con.execute("INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES ('Maíz', 'maiz', 'cereal', 120)")
        con.execute("INSERT INTO plan (nombre) VALUES ('Mi plan')")
        con.execute("INSERT INTO parcela (plan_id, nombre, clave, hectareas) VALUES (1, 'Lote', 'lote', 5)")
        con.execute("INSERT INTO siembra (parcela_id, cultivo_id, fecha_siembra, fecha_cosecha, hectareas) VALUES (1, 1, '2030-01-01', '2030-05-01', 5)")
        for nombre, clave in [("Monterrey, NL", "monterrey, nl"), ("My location", "my location")]:
            con.execute("INSERT INTO ubicacion (nombre, clave, lat, lon, zona) VALUES (?, ?, 1, 1, 'UTC')", (nombre, clave))
        con.execute("PRAGMA user_version = 4")
        con.commit()
        con.close()
        with patch.object(config, "DB_PATH", ruta):
            db.iniciar()
            db.iniciar()  # una segunda vez no debe fallar ni duplicar columnas
            con = db.conectar()
            columnas = {f["name"] for f in con.execute("PRAGMA table_info(siembra)")}
            self.assertTrue({"rendimiento_t_ha", "precio_t", "costo_ha"} <= columnas)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM siembra").fetchone()[0], 1)  # los datos siguen ahí
            self.assertIsNone(con.execute("SELECT rendimiento_t_ha FROM siembra").fetchone()[0])
            con.execute("INSERT INTO tarea (siembra_id, titulo, fecha) VALUES (1, 'Prueba', '2030-02-01')")
            con.execute("DELETE FROM siembra WHERE id = 1")  # las tareas se borran con la siembra
            self.assertEqual(con.execute("SELECT COUNT(*) FROM tarea").fetchone()[0], 0)
            estados_guardados = {f["nombre"]: f["cve_ent"] for f in con.execute("SELECT nombre, cve_ent FROM ubicacion")}
            self.assertEqual(estados_guardados, {"Monterrey, NL": "19", "My location": None})
            self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.VERSION_ESQUEMA)
            con.close()


if __name__ == "__main__":
    unittest.main()
