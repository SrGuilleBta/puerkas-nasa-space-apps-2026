"""Pruebas del modo solo lectura: bloquea todo lo que modifica y deja pasar las consultas (sin red)."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Antes de importar la app: así la base apunta a una carpeta temporal y nunca a la real.
os.environ.setdefault("PLANIFICADOR_DB", str(Path(tempfile.mkdtemp()) / "prueba.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402


class SoloLectura(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cliente = TestClient(app)
        cls.cliente.__enter__()  # corre el arranque (crea la base de demo)

    @classmethod
    def tearDownClass(cls):
        cls.cliente.__exit__(None, None, None)

    def test_bloquea_todo_lo_que_modifica(self):
        casos = [
            ("POST", "/api/planificador/planes", {"nombre": "x"}),
            ("PATCH", "/api/planificador/planes/1", {"nombre": "x"}),
            ("DELETE", "/api/planificador/planes/1", None),
            ("POST", "/api/ubicaciones", {"nombre": "x", "lat": 20, "lon": -100, "zona": "UTC"}),
            ("PUT", "/api/ubicaciones/mi-ubicacion", {"lat": 20, "lon": -100, "zona": "UTC"}),
            ("DELETE", "/api/ubicaciones/1", None),
        ]
        with patch.object(config, "SOLO_LECTURA", True):
            for metodo, ruta, cuerpo in casos:
                with self.subTest(metodo=metodo, ruta=ruta):
                    r = self.cliente.request(metodo, ruta, json=cuerpo)
                    self.assertEqual(r.status_code, 403)
                    self.assertIn("read-only", r.json()["detail"])

    def test_no_cambia_nada_en_la_base(self):
        antes = self.cliente.get("/api/planificador/planes").json()
        with patch.object(config, "SOLO_LECTURA", True):
            self.cliente.post("/api/planificador/planes", json={"nombre": "intruso"})
            self.cliente.delete(f"/api/planificador/planes/{antes[0]['id']}")
        self.assertEqual(self.cliente.get("/api/planificador/planes").json(), antes)

    def test_las_consultas_siguen_funcionando(self):
        with patch.object(config, "SOLO_LECTURA", True):
            self.assertEqual(self.cliente.get("/api/planificador/planes").status_code, 200)
            self.assertEqual(self.cliente.get("/api/ubicaciones").status_code, 200)
            salud = self.cliente.get("/api/health").json()
        self.assertTrue(salud["readOnly"])

    def test_apagado_deja_escribir(self):
        with patch.object(config, "SOLO_LECTURA", False):
            r = self.cliente.post("/api/planificador/planes", json={"nombre": "Plan de prueba"})
            self.assertEqual(r.status_code, 201)
            self.cliente.delete(f"/api/planificador/planes/{r.json()['id']}")
            self.assertFalse(self.cliente.get("/api/health").json()["readOnly"])


if __name__ == "__main__":
    unittest.main()
