"""Pruebas del motor de plagas: reglas de riesgo, caché, orquestación con EPPO simulado y su uso en las alertas.

Nada de esto sale a internet: EPPO, GBIF, iNaturalist y Open-Meteo se simulan.
"""

import asyncio
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

# Antes de importar la app: así la base y la caché apuntan a carpetas temporales y nunca a las reales.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))
os.environ.setdefault("PLAGAS_CACHE", str(Path(tempfile.mkdtemp()) / "cache"))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import alertas  # noqa: E402
from app.services import plagas as motor  # noqa: E402
from app.services.plagas import cache, clima, eppo, evaluar, presencia  # noqa: E402
from app.services.ubicaciones import Ubicacion  # noqa: E402

LUGAR = Ubicacion(1, "Monterrey, NL", 25.67, -100.31, "America/Monterrey")
SIN_REGISTROS = {"detectada": False, "radioKm": 100.0, "registros": 0, "masCercanoKm": None, "lugar": None, "ultimoRegistro": None}
CON_REGISTROS = {**SIN_REGISTROS, "detectada": True, "registros": 3, "masCercanoKm": 40.0, "lugar": "Nuevo León"}


def serie(n=10, tmax=30, tmin=18, humedad=60, lluvia=10):
    return [{"fecha": f"2026-11-{i + 1:02d}", "tmax": tmax, "tmin": tmin, "tmed": (tmax + tmin) / 2,
             "humedad": humedad, "lluvia": lluvia} for i in range(n)]


class PruebasEvaluar(unittest.TestCase):
    def test_solo_cuenta_las_plagas_presentes_en_el_pais(self):
        registros = [
            {"eppocode": "AAA", "prefname": "Alpha", "peststatus": "A", "yr_situation": "2001", "yr_erad": None},
            {"eppocode": "bbb", "prefname": "Beta", "peststatus": "D", "yr_erad": None},  # ausente
            {"eppocode": "CCC", "prefname": "Gamma", "peststatus": "A", "yr_erad": "1999"},  # erradicada
            {"eppocode": "DDD", "prefname": "Delta"},  # sin estado: "X"
            {"prefname": "Sin código"},
            "no es un registro",
        ]
        pais = evaluar.plagas_presentes(registros)
        self.assertEqual(sorted(pais), ["AAA", "DDD"])
        self.assertEqual(pais["AAA"]["estadoPais"], "Present (widespread) - Situation 2001")
        self.assertEqual(pais["DDD"]["estado"], "X")

    def test_tipo_biologico_segun_el_reino(self):
        self.assertEqual(evaluar.clasificar({"kingdom": "Animalia"}), "insect")
        self.assertEqual(evaluar.clasificar("Fungi"), "fungus")
        self.assertEqual(evaluar.clasificar("Chromista / Oomycota"), "fungus")
        self.assertEqual(evaluar.clasificar("Bacteria"), "pathogen")
        self.assertEqual(evaluar.clasificar("Plantae"), "weed")  # las malezas no se evalúan con clima
        self.assertEqual(evaluar.clasificar(None), "fungus")  # sin dato: la regla prudente

    def test_insecto_acumula_grados_dia(self):
        # Media 24 °C: 14 grados-día al día; con 10 días son 140 (>= 65) y todos los días son favorables
        c = evaluar.evaluar_clima("insect", serie(10, tmax=30, tmin=18, humedad=60))
        self.assertEqual((c["nivelClima"], c["gradosDia"], c["rachaDias"]), ("high", 140.0, 10))
        # 4 días a 14 °C de media: 16 grados-día -> bajo
        frio = evaluar.evaluar_clima("insect", serie(4, tmax=20, tmin=8, humedad=60))
        self.assertEqual(frio["nivelClima"], "low")
        # Entre 45 y 65: medio. 4 días a 22 °C (media) -> 48
        medio = evaluar.evaluar_clima("insect", serie(4, tmax=28, tmin=16, humedad=60))
        self.assertEqual((medio["nivelClima"], medio["gradosDia"]), ("medium", 48.0))

    def test_insecto_con_aire_seco_o_calor_extremo_no_cuenta_dias_favorables(self):
        seco = evaluar.evaluar_clima("insect", serie(10, tmax=30, tmin=18, humedad=30))
        self.assertEqual(seco["diasFavorables"], [])
        self.assertEqual(seco["nivelClima"], "high")  # los grados-día se suman aunque el aire esté seco: es la regla del motor

    def test_hongo_necesita_dias_seguidos_con_humedad(self):
        humedo = serie(2, tmax=24, tmin=14, humedad=90)
        seco = serie(1, tmax=24, tmin=14, humedad=40, lluvia=0)
        # 3 días húmedos seguidos -> alto
        self.assertEqual(evaluar.evaluar_clima("fungus", humedo + serie(1, 24, 14, 90))["nivelClima"], "high")
        # 2 días húmedos -> medio
        self.assertEqual(evaluar.evaluar_clima("fungus", humedo + seco)["nivelClima"], "medium")
        # días húmedos separados por uno seco no suman racha
        alternado = serie(1, 24, 14, 90) + seco + serie(1, 24, 14, 90) + seco
        self.assertEqual(evaluar.evaluar_clima("fungus", alternado)["nivelClima"], "low")
        # la probabilidad de lluvia también cuenta
        lluvioso = serie(3, tmax=24, tmin=14, humedad=40, lluvia=70)
        self.assertEqual(evaluar.evaluar_clima("fungus", lluvioso)["nivelClima"], "high")
        # demasiado calor para el hongo
        self.assertEqual(evaluar.evaluar_clima("fungus", serie(5, 38, 28, 90))["nivelClima"], "low")

    def test_un_registro_cercano_sube_el_riesgo_a_critico(self):
        alto = {"nivelClima": "high"}
        self.assertEqual(evaluar.riesgo(alto, CON_REGISTROS)["nivel"], "critical")
        self.assertEqual(evaluar.riesgo(alto, SIN_REGISTROS)["nivel"], "high")
        self.assertEqual(evaluar.riesgo({"nivelClima": "medium"}, CON_REGISTROS)["nivel"], "medium")  # sin clima favorable no sube
        self.assertEqual(evaluar.riesgo({"nivelClima": "low"}, CON_REGISTROS)["nivel"], "low")

    def test_expediente_lee_el_formato_real_de_eppo(self):
        """Formas de respuesta tomadas de consultas reales a EPPO (lang_iso, class_label, files, country_iso)."""
        crudo = {
            "kingdom": {"eppocode": {"eppocode": "1ANIMK", "prefname": "Animalia"}},
            "names": [
                {"lang_iso": "de", "fullname": "Heerwurm", "preferred": False},
                {"lang_iso": "en", "fullname": "fall armyworm", "preferred": False},
                {"lang_iso": "en", "fullname": "grass worm", "preferred": False},
                {"lang_iso": "es", "fullname": "gusano cogollero del maíz", "preferred": False},
                {"lang_iso": "la", "fullname": "Laphygma frugiperda", "preferred": False},
                {"lang_iso": "la", "fullname": "Spodoptera frugiperda", "preferred": True, "author": "(Smith)"},
            ],
            "hosts": [
                {"eppocode": "AAAAA", "prefname": "Alfa", "class_label": "Host"},
                {"eppocode": "ZEAMX", "prefname": "Zea mays", "class_label": "Major host"},
                {"eppocode": "EXPER", "prefname": "Experimental plant", "class_label": "Experimental"},
                {"eppocode": "SORVU", "prefname": "Sorghum bicolor", "class_label": "Major host"},
            ],
            "vectors": [{"eppocode": "CERMRU", "prefname": "Cerotoma ruficornis", "vectorclass_label": "Potential vector"}],
            "bcas": [{"fullname": "Telenomus remus"}],
            "categorization": [
                {"country_iso": "EG", "country_name": "Egypt", "qlist": "1", "qlist_label": "A1 list"},
                {"country_iso": "MX", "country_name": "Mexico", "qlist": "2", "qlist_label": "A2 list"},
            ],
            "photos": [{"photo_id": 1, "files": [{"size": "220x130", "url": "https://x/p220.jpg"}, {"size": "1024x0", "url": "https://x/p1024.jpg"}]},
                       {"photo_id": 2, "files": [{"size": "220x130", "url": "https://x/solo.jpg"}]}],
        }
        e = evaluar.expediente("LAPHFR", crudo, {"nombre": "Spodoptera frugiperda", "estadoPais": "Present (widespread)"})
        self.assertEqual((e["nombre"], e["nombreEs"], e["nombreCientifico"], e["tipo"]),
                         ("Fall armyworm", "Gusano cogollero del maíz", "Spodoptera frugiperda", "insect"))
        self.assertEqual(e["otrosNombres"], ["Grass worm"])
        self.assertEqual(e["hospederos"], ["Zea mays (ZEAMX)", "Sorghum bicolor (SORVU)"])  # solo los principales
        self.assertEqual(e["vectores"], ["Cerotoma ruficornis"])
        self.assertEqual(e["controlBiologico"], ["Telenomus remus"])
        self.assertEqual(e["cuarentena"], ["Mexico: A2 list"])  # solo México
        self.assertEqual(e["fotos"], ["https://x/p1024.jpg", "https://x/solo.jpg"])

    def test_sin_hospederos_principales_muestra_pocos_comunes_y_ninguno_experimental(self):
        crudo = {"hosts": [{"prefname": f"Host {i}", "class_label": "Host"} for i in range(8)] + [{"prefname": "Exp", "class_label": "Experimental"}]}
        e = evaluar.expediente("XXXXXX", crudo, {})
        self.assertEqual(e["hospederos"], ["Host 0", "Host 1", "Host 2"])

    def test_clase_de_hospedero_prioriza_y_descarta(self):
        self.assertEqual(evaluar.clase_de({"class_label": "Major host"}), 0)
        self.assertEqual(evaluar.clase_de({"class_label": "Host"}), 1)
        self.assertEqual(evaluar.clase_de({}), 1)  # sin dato, como hospedero común
        self.assertIsNone(evaluar.clase_de({"class_label": "Experimental"}))
        self.assertIsNone(evaluar.clase_de({"class_label": "Doubtful host"}))

    def test_expediente_con_respuestas_vacias_no_falla(self):
        e = evaluar.expediente("XXXXXX", {}, {"nombre": "Pestis ignota"})
        self.assertEqual((e["nombre"], e["tipo"], e["hospederos"], e["fotos"]), ("Pestis ignota", "fungus", [], []))

    def test_resumen_cuenta_por_nivel(self):
        r = evaluar.resumen([{"riesgo": "low"}, {"riesgo": "high"}, {"riesgo": "high"}, {"riesgo": "medium"}])
        self.assertEqual(r, {"nivel": "high", "conteo": {"critical": 0, "high": 2, "medium": 1, "low": 1}})
        self.assertEqual(evaluar.resumen([])["nivel"], "low")


class PruebasClima(unittest.TestCase):
    def test_dias_pasados_deducen_la_lluvia_de_lo_medido_y_se_omiten_los_incompletos(self):
        datos = {"daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04"],
            "temperature_2m_max": [30, 28, None, 29],
            "temperature_2m_min": [18, 17, 16, 15],
            "temperature_2m_mean": [24.04, 22.5, 20, 22],
            "relative_humidity_2m_mean": [60, 70, 80, 90],
            "precipitation_probability_max": [None, None, 10, 40],
            "precipitation_sum": [3.0, 0.2, 0, 0],
        }}
        dias = clima.serie_desde_respuesta(datos)
        self.assertEqual([d["fecha"] for d in dias], ["2026-11-01", "2026-11-02", "2026-11-04"])
        self.assertEqual([d["lluvia"] for d in dias], [100, 0, 40])
        self.assertEqual(dias[0]["tmed"], 24.0)

    def test_respuesta_inesperada_da_error_claro(self):
        with self.assertRaises(clima.ErrorClima):
            clima.serie_desde_respuesta({"nada": 1})


class PruebasCache(unittest.TestCase):
    def test_guarda_lee_y_caduca(self):
        with tempfile.TemporaryDirectory() as carpeta, patch.object(cache, "CARPETA", Path(carpeta)):
            self.assertIsNone(cache.leer("x", "../../raro nombre", 1))
            cache.escribir("x", "../../raro nombre", {"a": [1, 2]})  # la clave no puede escapar de la carpeta
            self.assertEqual(cache.leer("x", "../../raro nombre", 1), {"a": [1, 2]})
            self.assertEqual(list(Path(carpeta).rglob("*.json"))[0].parent, Path(carpeta) / "x")
            with patch("app.services.plagas.cache.time.time", return_value=__import__("time").time() + 3 * cache.DIA):
                self.assertIsNone(cache.leer("x", "../../raro nombre", 1))  # venció
                self.assertEqual(cache.leer("x", "../../raro nombre", 5), {"a": [1, 2]})

    def test_archivo_danado_se_ignora(self):
        with tempfile.TemporaryDirectory() as carpeta, patch.object(cache, "CARPETA", Path(carpeta)):
            cache.escribir("x", "k", {"a": 1})
            next(Path(carpeta).rglob("*.json")).write_text("{no es json", encoding="utf-8")
            self.assertIsNone(cache.leer("x", "k", 1))


class PruebasPresencia(unittest.TestCase):
    def test_nombre_de_especie(self):
        self.assertEqual(presencia.especie("Spodoptera frugiperda (J.E. Smith)"), "Spodoptera frugiperda")
        self.assertEqual(presencia.especie("Candidatus Liberibacter asiaticus"), "Liberibacter asiaticus")
        self.assertEqual(presencia.especie("Fusarium"), "Fusarium")

    def test_resumir_toma_el_registro_mas_cercano(self):
        r = presencia.resumir([
            {"fuente": "GBIF", "distanciaKm": 80.0, "lugar": "A", "fecha": "2020"},
            {"fuente": "iNaturalist", "distanciaKm": 12.5, "lugar": "B", "fecha": "2025-01-01"},
        ])
        self.assertEqual((r["detectada"], r["registros"], r["masCercanoKm"], r["lugar"]), (True, 2, 12.5, "B"))
        self.assertFalse(presencia.resumir([])["detectada"])

    def test_no_guarda_en_cache_si_una_fuente_fallo(self):
        async def correr(gbif, inat):
            with patch.object(presencia, "_gbif", AsyncMock(return_value=gbif)), \
                    patch.object(presencia, "_inat", AsyncMock(return_value=inat)):
                return await presencia.cerca(None, "Pestis alba", 25.7, -100.3)

        with tempfile.TemporaryDirectory() as carpeta, patch.object(cache, "CARPETA", Path(carpeta)):
            r = asyncio.run(correr(None, []))  # GBIF no respondió
            self.assertFalse(r["detectada"])
            self.assertEqual(list(Path(carpeta).rglob("*.json")), [])  # "sin registros" sería falso: no se guarda
            asyncio.run(correr([], []))  # las dos respondieron
            self.assertEqual(len(list(Path(carpeta).rglob("*.json"))), 1)


class PruebasClienteEppo(unittest.TestCase):
    """El cliente HTTP de EPPO con respuestas simuladas (httpx.MockTransport)."""

    def correr(self, manejador, coro):
        async def principal():
            async with httpx.AsyncClient(transport=httpx.MockTransport(manejador)) as cliente:
                return await coro(cliente)

        with patch.object(config, "EPPO_API_KEY", "llave-de-prueba"), patch.object(eppo.asyncio, "sleep", AsyncMock()):
            return asyncio.run(principal())

    def test_manda_la_llave_y_devuelve_el_json(self):
        vistos = []

        def manejador(peticion):
            vistos.append(peticion)
            return httpx.Response(200, json=[{"eppocode": "AAA"}])

        r = self.correr(manejador, lambda c: eppo.pedir(c, "/taxons/taxon/ZEAMX/pests"))
        self.assertEqual(r, [{"eppocode": "AAA"}])
        self.assertEqual(str(vistos[0].url), "https://api.eppo.int/gd/v2/taxons/taxon/ZEAMX/pests")
        self.assertEqual(vistos[0].headers["X-Api-Key"], "llave-de-prueba")

    def test_404_es_none_y_401_es_llave_rechazada(self):
        self.assertIsNone(self.correr(lambda p: httpx.Response(404), lambda c: eppo.pedir(c, "x")))
        with self.assertRaisesRegex(eppo.ErrorEppo, "API key"):
            self.correr(lambda p: httpx.Response(401), lambda c: eppo.pedir(c, "x"))

    def test_reintenta_ante_429_y_se_rinde_despues_de_varios_intentos(self):
        respuestas = iter([httpx.Response(429), httpx.Response(503), httpx.Response(200, json={"ok": 1})])
        self.assertEqual(self.correr(lambda p: next(respuestas), lambda c: eppo.pedir(c, "x")), {"ok": 1})
        intentos = []

        def siempre_429(peticion):
            intentos.append(1)
            return httpx.Response(429)

        with self.assertRaises(eppo.ErrorEppo):
            self.correr(siempre_429, lambda c: eppo.pedir(c, "x"))
        self.assertEqual(len(intentos), eppo.REINTENTOS + 1)

    def test_sin_llave_no_sale_a_internet(self):
        async def principal():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda p: self.fail("no debía pedir nada"))) as c:
                await eppo.pedir(c, "x")

        with patch.object(config, "EPPO_API_KEY", ""), self.assertRaises(eppo.SinLlave):
            asyncio.run(principal())

    def test_diccionarios_encuentra_objetos_anidados(self):
        datos = {"data": {"resultados": [{"eppocode": "AAA"}]}, "otros": [[{"fullname": "Beta"}], {"ruido": 1}], "total": 2}
        self.assertEqual([d.get("eppocode") or d.get("fullname") for d in eppo.diccionarios(datos)], ["AAA", "Beta", None])  # un objeto dentro de una lista se devuelve tal cual
        self.assertEqual(eppo.diccionarios(None), [])

    def test_el_expediente_solo_se_guarda_si_todos_los_endpoints_respondieron(self):
        def completo(peticion):
            return httpx.Response(200, json={"fullname": peticion.url.path.rsplit("/", 1)[-1]})

        def con_fallo(peticion):
            return httpx.Response(500) if peticion.url.path.endswith("/photos") else completo(peticion)

        with tempfile.TemporaryDirectory() as carpeta, patch.object(cache, "CARPETA", Path(carpeta)):
            crudo = self.correr(con_fallo, lambda c: eppo.expediente_crudo(c, "AAA"))
            self.assertIsNone(crudo["photos"])
            self.assertEqual(crudo["names"], {"fullname": "names"})
            self.assertEqual(list(Path(carpeta).rglob("*.json")), [])  # incompleto: se vuelve a pedir la próxima vez
            self.correr(completo, lambda c: eppo.expediente_crudo(c, "AAA"))
            self.assertEqual(len(list(Path(carpeta).rglob("*.json"))), 1)
            # con el expediente guardado ya no se consulta EPPO
            otro = self.correr(lambda p: self.fail("no debía pedir nada"), lambda c: eppo.expediente_crudo(c, "AAA"))
            self.assertEqual(otro["kingdom"], {"fullname": "kingdom"})


PAIS = {
    "AAA": {"eppocode": "AAA", "nombre": "Alpha insect", "estado": "A", "estadoPais": "Present (widespread)"},
    "BBB": {"eppocode": "BBB", "nombre": "Beta fungus", "estado": "B", "estadoPais": "Present (restricted distribution)"},
    "WWW": {"eppocode": "WWW", "nombre": "Weedy weed", "estado": "A", "estadoPais": "Present (widespread)"},
}
CRUDO = {
    "AAA": {"kingdom": "Animalia", "names": [{"isolang": "en", "fullname": "Alpha bug"}]},
    "BBB": {"kingdom": "Fungi", "names": [{"isolang": "en", "fullname": "Beta blight"}]},
    "WWW": {"kingdom": "Plantae"},
}


def simulado(en_cultivo=("AAA", "BBB", "WWW", "ZZZ"), presencia_aaa=CON_REGISTROS, dias=None):
    """Parches para que `analizar` no salga a internet."""
    dias = dias or serie(10, tmax=30, tmin=18, humedad=90)

    async def expediente(_cliente, codigo):
        return CRUDO[codigo]

    async def cerca(_cliente, nombre, lat, lon):
        return presencia_aaa if "Alpha" in nombre else SIN_REGISTROS

    return [
        patch.object(motor, "plagas_mx", return_value=PAIS),
        patch.object(clima, "serie", AsyncMock(return_value=dias)),
        patch.object(eppo, "plagas_de_cultivo", AsyncMock(return_value=[{"eppocode": c} for c in en_cultivo])),
        patch.object(eppo, "expediente_crudo", expediente),
        patch.object(presencia, "cerca", cerca),
    ]


class Parchado(unittest.TestCase):
    def aplicar(self, parches):
        for p in parches:
            p.start()
            self.addCleanup(p.stop)


class PruebasAnalisis(Parchado):
    def test_cruza_con_el_pais_omite_malezas_y_ordena_por_riesgo(self):
        self.aplicar(simulado())
        r = asyncio.run(motor.analizar("zeamx", LUGAR))
        self.assertEqual(r["eppocode"], "ZEAMX")
        # ZZZ no está en el país y WWW es maleza: quedan AAA (crítica, con registros) y BBB (alta)
        self.assertEqual([(p["eppocode"], p["riesgo"]) for p in r["plagas"]], [("AAA", "critical"), ("BBB", "high")])
        self.assertEqual((r["totalEnPais"], r["analizadas"], r["nivel"]), (3, 2, "critical"))
        self.assertEqual(r["conteo"], {"critical": 1, "high": 1, "medium": 0, "low": 0})
        self.assertEqual(r["plagas"][0]["nombre"], "Alpha bug")
        self.assertEqual(r["ventana"], {"desde": "2026-11-01", "hasta": "2026-11-10"})

    def test_analiza_primero_las_plagas_principales_del_cultivo_y_omite_las_experimentales(self):
        pais = {c: {"eppocode": c, "nombre": c, "estado": "A", "estadoPais": "Present"} for c in ("AAA", "BBB", "CCC", "DDD")}
        lista = [
            {"eppocode": "AAA", "class_label": "Host"},
            {"eppocode": "BBB", "class_label": "Major host"},
            {"eppocode": "CCC", "class_label": "Experimental"},
            {"eppocode": "DDD", "class_label": "Doubtful host"},
        ]
        vistos = []

        async def expediente(_c, codigo):
            vistos.append(codigo)
            return {"kingdom": "Fungi", "names": []}

        parches = simulado()
        parches[0] = patch.object(motor, "plagas_mx", return_value=pais)
        parches[2] = patch.object(eppo, "plagas_de_cultivo", AsyncMock(return_value=lista))
        parches[3] = patch.object(eppo, "expediente_crudo", expediente)
        self.aplicar(parches)
        r = asyncio.run(motor.analizar("ZEAMX", LUGAR))
        self.assertEqual(sorted(vistos), ["AAA", "BBB"])  # CCC y DDD ni se consultan
        self.assertEqual(r["totalEnPais"], 2)

    def test_respeta_el_limite_de_plagas(self):
        codigos = [f"P{i:02d}" for i in range(30)]
        pais = {c: {"eppocode": c, "nombre": c, "estado": "A", "estadoPais": "Present"} for c in codigos}
        crudo = {"kingdom": "Fungi", "names": []}

        async def expediente(_c, _codigo):
            return crudo

        parches = simulado(en_cultivo=codigos)
        parches[0] = patch.object(motor, "plagas_mx", return_value=pais)
        parches[3] = patch.object(eppo, "expediente_crudo", expediente)
        self.aplicar(parches)
        r = asyncio.run(motor.analizar("ZEAMX", LUGAR))
        self.assertEqual(r["analizadas"], motor.LIMITE_PLAGAS)
        self.assertEqual(r["totalEnPais"], 30)

    def test_si_eppo_falla_en_todas_no_inventa_un_todo_bien(self):
        parches = simulado()

        async def falla(_c, _codigo):
            raise eppo.ErrorEppo("EPPO responded with 500")

        parches[3] = patch.object(eppo, "expediente_crudo", falla)
        self.aplicar(parches)
        with self.assertRaises(eppo.ErrorEppo):
            asyncio.run(motor.analizar("ZEAMX", LUGAR))

    def test_si_falla_una_sola_plaga_el_resto_sale_y_se_marca_incompleto(self):
        parches = simulado()

        async def expediente(_c, codigo):
            if codigo == "BBB":
                raise eppo.ErrorEppo("EPPO responded with 500")
            return CRUDO[codigo]

        parches[3] = patch.object(eppo, "expediente_crudo", expediente)
        self.aplicar(parches)
        r = asyncio.run(motor.analizar("ZEAMX", LUGAR))
        self.assertEqual([p["eppocode"] for p in r["plagas"]], ["AAA"])
        self.assertTrue(r["incompleto"])

    def test_sin_clima_el_cultivo_no_esta_disponible(self):
        parches = simulado()
        parches[1] = patch.object(clima, "serie", AsyncMock(side_effect=clima.ErrorClima("sin clima")))
        self.aplicar(parches)
        with self.assertRaises(motor.PlagasNoDisponibles):
            asyncio.run(motor.analizar("ZEAMX", LUGAR))


class PruebasPedir(Parchado):
    def setUp(self):
        motor._resultados.clear()
        motor._errores.clear()
        motor._tareas.clear()
        self.aplicar([patch.object(config, "EPPO_API_KEY", "llave-de-prueba")])

    def test_sin_codigo_o_sin_llave_no_hay_calculo(self):
        async def correr():
            self.assertEqual(motor.pedir(None, LUGAR)["estado"], "no_disponible")
            with patch.object(config, "EPPO_API_KEY", ""):
                self.assertEqual(motor.pedir("ZEAMX", LUGAR)["estado"], "no_disponible")
                self.assertEqual(motor.para_alertas({"maiz": {"eppocode": "ZEAMX"}}, LUGAR), {})
            self.assertEqual(motor._tareas, {})

        asyncio.run(correr())

    def test_primero_calcula_en_segundo_plano_y_despues_sale_de_la_cache(self):
        self.aplicar(simulado())

        async def correr():
            self.assertEqual(motor.pedir("ZEAMX", LUGAR), {"estado": "calculando"})
            self.assertEqual(motor.pedir("ZEAMX", LUGAR), {"estado": "calculando"})  # no arranca un segundo cálculo
            self.assertEqual(len(motor._tareas), 1)
            await asyncio.gather(*list(motor._tareas.values()))
            listo = motor.pedir("zeamx", LUGAR)  # el código no distingue mayúsculas
            self.assertEqual((listo["estado"], listo["nivel"]), ("listo", "critical"))
            self.assertIsNotNone(motor.en_cache("ZEAMX", LUGAR))
            self.assertIsNone(motor.en_cache("OTRO", LUGAR))

        asyncio.run(correr())

    def test_un_fallo_se_recuerda_unos_minutos_sin_reintentar(self):
        parches = simulado()
        parches[1] = patch.object(clima, "serie", AsyncMock(side_effect=clima.ErrorClima("sin clima")))
        self.aplicar(parches)

        async def correr():
            motor.pedir("ZEAMX", LUGAR)
            await asyncio.gather(*list(motor._tareas.values()))
            r = motor.pedir("ZEAMX", LUGAR)
            self.assertEqual((r["estado"], r["mensaje"]), ("error", "sin clima"))
            self.assertEqual(motor._tareas, {})  # no se lanzó otro intento

        asyncio.run(correr())

    def test_para_alertas_devuelve_solo_lo_ya_calculado_y_pide_el_resto(self):
        self.aplicar(simulado())
        fichas = {"maiz-grano": {"eppocode": "ZEAMX"}, "sin-codigo": {"eppocode": None}}

        async def correr():
            self.assertEqual(motor.para_alertas(fichas, LUGAR), {})  # aún calculando
            await asyncio.gather(*list(motor._tareas.values()))
            r = motor.para_alertas(fichas, LUGAR)
            self.assertEqual(list(r), ["maiz-grano"])
            self.assertEqual(r["maiz-grano"]["estado"], "listo")

        asyncio.run(correr())


def resultado(plagas, nivel):
    return {"estado": "listo", "nivel": nivel, "plagas": plagas}


def plaga(nombre, riesgo):
    return {"nombre": nombre, "riesgo": riesgo}


def clima_del_dia():
    return {"pronostico": [{"fecha": "2026-11-11", "tmax": 24, "tmin": 12, "lluvia": 10, "cielo": "sol"}],
            "hoy": {"temperatura": 22, "humedad": 55, "vientoKmh": 10}}


class PruebasAlertasConMotor(unittest.TestCase):
    def siembra(self, nombre, tipo, catalogo_id):
        return {"cultivo": {"nombre": nombre, "tipo": tipo, "catalogo_id": catalogo_id}}

    def test_aviso_nombra_solo_las_plagas_criticas_y_dice_que_no_es_una_deteccion(self):
        plagas = {"maiz": resultado([plaga("Fall armyworm", "critical"), plaga("Corn earworm", "critical"),
                                     plaga("Corn rust", "high"), plaga("Mite", "low")], "critical")}
        r = alertas.calcular(clima_del_dia(), [self.siembra("Grain maize", "cereal", "maiz")], date(2026, 11, 11), {}, None, None, plagas)
        a = next(x for x in r if x["id"] == "plagas-maiz")
        self.assertEqual((a["tipo"], a["nivel"], a["cultivos"]), ("plaga", "alta", ["Grain maize"]))
        self.assertIn("Fall armyworm, Corn earworm", a["detalle"])
        self.assertIn("they have been recorded within 100 km", a["detalle"])
        self.assertNotIn("Corn rust", a["detalle"])  # las de riesgo alto no avisan: están en la guía del cultivo
        self.assertNotIn("Mite", a["detalle"])
        self.assertIn("not a detection", a["detalle"])

    def test_con_una_sola_critica_el_texto_va_en_singular_y_con_mas_de_tres_dice_cuantas_faltan(self):
        una = {"maiz": resultado([plaga("Fall armyworm", "critical")], "critical")}
        r = alertas.calcular(clima_del_dia(), [self.siembra("Grain maize", "cereal", "maiz")], date(2026, 11, 11), {}, None, None, una)
        detalle = next(x for x in r if x["id"] == "plagas-maiz")["detalle"]
        self.assertIn("Watch for Fall armyworm. The weather favors it and it has been recorded", detalle)
        cinco = {"maiz": resultado([plaga(f"Pest {i}", "critical") for i in range(5)], "critical")}
        r = alertas.calcular(clima_del_dia(), [self.siembra("Grain maize", "cereal", "maiz")], date(2026, 11, 11), {}, None, None, cinco)
        self.assertIn("Pest 0, Pest 1, Pest 2 and 2 more", next(x for x in r if x["id"] == "plagas-maiz")["detalle"])

    def test_riesgo_alto_medio_o_bajo_no_avisa(self):
        plagas = {"maiz": resultado([plaga("Corn rust", "high"), plaga("Mite", "medium"), plaga("Rust", "low")], "high")}
        r = alertas.calcular(clima_del_dia(), [self.siembra("Grain maize", "cereal", "maiz")], date(2026, 11, 11), {}, None, None, plagas)
        self.assertEqual([a for a in r if a["tipo"] == "plaga"], [])

    def test_el_cultivo_con_motor_deja_de_recibir_las_reglas_generales(self):
        calor = {"pronostico": [{"fecha": "2026-11-11", "tmax": 33, "tmin": 20, "lluvia": 0, "cielo": "sol"}],
                 "hoy": {"temperatura": 28, "humedad": 40, "vientoKmh": 5}}
        activos = [self.siembra("Grain maize", "cereal", "maiz"), self.siembra("Tomato", "hortaliza", "tomate")]
        sin_motor = alertas.calcular(calor, activos, date(2026, 11, 11), {}, None, None, None)
        self.assertIn("cogollero", [a["id"] for a in sin_motor])
        self.assertIn("chupadores", [a["id"] for a in sin_motor])
        # El maíz ya tiene análisis (sin riesgo): su regla general (gusano cogollero) se va; el tomate la conserva
        con_motor = alertas.calcular(calor, activos, date(2026, 11, 11), {}, None, None,
                                     {"maiz": resultado([plaga("Mite", "low")], "low")})
        ids = [a["id"] for a in con_motor]
        self.assertNotIn("cogollero", ids)
        self.assertIn("chupadores", ids)

    def test_las_alertas_siguen_igual_sin_motor(self):
        r = alertas.calcular(clima_del_dia(), [self.siembra("Grain maize", "cereal", "maiz")], date(2026, 11, 11))
        self.assertEqual(r, [])


class PruebasEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if Path(config.DB_PATH).name == "planificador.db":
            raise RuntimeError("Las pruebas apuntan a la base real; define PLANIFICADOR_DB antes de importar app")
        cls._ctx = TestClient(app)
        cls.c = cls._ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def test_devuelve_el_estado_del_motor_con_el_nombre_del_cultivo(self):
        from app.services import catalogo_cultivos

        ficha = catalogo_cultivos.ficha_del_catalogo("maiz-grano")
        with patch.object(motor, "pedir", return_value={"estado": "calculando"}) as m:
            r = self.c.get("/api/planificador/catalogo/maiz-grano/plagas", params={"municipio": "Monterrey, NL"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"catalogoId": "maiz-grano", "cultivo": ficha["nombre"], "estado": "calculando"})
        self.assertEqual(m.call_args.args[0], ficha.get("eppocode"))  # usa el código EPPO del catálogo

    def test_cultivo_o_ubicacion_desconocidos_dan_404(self):
        self.assertEqual(self.c.get("/api/planificador/catalogo/no-existe/plagas", params={"municipio": "Monterrey, NL"}).status_code, 404)
        self.assertEqual(self.c.get("/api/planificador/catalogo/maiz-grano/plagas", params={"municipio": "Narnia"}).status_code, 404)

    def test_alertas_y_noticias_usan_el_motor_cuando_ya_hay_analisis(self):
        """El cultivo en curso (maíz de la demo) pasa de las reglas generales al aviso del motor en cuanto hay análisis."""
        import time

        from app import db
        from app.services import nasa_power, suelo_ubicacion
        from app.services import clima as clima_servicio

        motor._resultados.clear()
        motor._errores.clear()
        hoy = db.hoy().isoformat()
        clima_falso = {"pronostico": [{"fecha": hoy, "tmax": 24, "tmin": 12, "lluvia": 10, "cielo": "sol"}],
                       "hoy": {"temperatura": 22, "humedad": 55, "vientoKmh": 10}}
        parches = simulado() + [
            patch.object(config, "EPPO_API_KEY", "llave-de-prueba"),
            patch.object(clima_servicio, "clima", AsyncMock(return_value=clima_falso)),
            patch.object(nasa_power, "periodo", AsyncMock(side_effect=nasa_power.ErrorNasaPower("sin red"))),
            patch.object(suelo_ubicacion, "humedad_vs_normal", AsyncMock(return_value=None)),
        ]
        for pa in parches:
            pa.start()
            self.addCleanup(pa.stop)

        params = {"municipio": "Monterrey, NL"}
        primera = self.c.get("/api/principal/alertas", params=params).json()
        self.assertFalse([a for a in primera if a["id"].startswith("plagas-")])  # todavía calculando: nada del motor
        limite = time.monotonic() + 10
        while not motor._resultados and time.monotonic() < limite:
            time.sleep(0.05)
        self.assertTrue(motor._resultados, "el análisis en segundo plano no terminó")

        segunda = self.c.get("/api/principal/alertas", params=params).json()
        avisos = [a for a in segunda if a["id"].startswith("plagas-")]
        self.assertTrue(avisos)
        self.assertTrue(all(a["tipo"] == "plaga" and a["nivel"] == "alta" for a in avisos))  # AAA tiene registros cercanos
        self.assertIn("Alpha bug", avisos[0]["detalle"])

        noticias = self.c.get("/api/noticias", params=params).json()["items"]
        self.assertTrue([n for n in noticias if n["id"].startswith("alerta-plagas-")])  # Noticias muestra el mismo aviso


if __name__ == "__main__":
    unittest.main()
