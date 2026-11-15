"""Base de datos SQLite del Planificador: esquema, conexión y datos de demo.

Modelo:  plan -> parcela -> siembra  (y siembra -> cultivo, del catálogo).
Las fechas se guardan como texto ISO (AAAA-MM-DD), que se ordena y compara bien como texto.

La primera vez que arranca (archivo nuevo) crea las tablas y carga datos de demo. Para volver
a empezar desde cero basta con borrar backend/data/planificador.db y reiniciar el backend.
"""

import sqlite3
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app import config

VERSION_ESQUEMA = 2  # versión actual de la base (ver iniciar)

# Zona horaria de referencia para "hoy" (el contenedor corre en UTC y de noche ya es mañana)
ZONA = ZoneInfo("America/Monterrey")


def hoy() -> date:
    return datetime.now(ZONA).date()


def clave(texto: str) -> str:
    """Nombre normalizado para comparar: sin acentos, sin mayúsculas, sin espacios de más.
    'Maíz  Amarillo' y 'maiz amarillo' dan la misma clave. (La comparación sin mayúsculas de
    SQLite solo cubre letras ASCII y no iguala 'Í' con 'í', por eso se hace aquí.)"""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sin_acentos.casefold().split())


ESQUEMA = """
CREATE TABLE IF NOT EXISTS cultivo (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT    NOT NULL,
    clave       TEXT    NOT NULL UNIQUE,     -- clave(nombre): evita duplicados 'Maíz'/'maiz'
    tipo        TEXT    NOT NULL,            -- cereal, leguminosa, frutal...
    ciclo_dias  INTEGER NOT NULL CHECK (ciclo_dias > 0)
);

CREATE TABLE IF NOT EXISTS plan (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parcela (
    id         INTEGER PRIMARY KEY,
    plan_id    INTEGER NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    nombre     TEXT    NOT NULL,
    clave      TEXT    NOT NULL,             -- clave(nombre), única dentro del plan
    hectareas  REAL    NOT NULL CHECK (hectareas > 0),
    UNIQUE (plan_id, clave)
);

CREATE TABLE IF NOT EXISTS siembra (
    id             INTEGER PRIMARY KEY,
    parcela_id     INTEGER NOT NULL REFERENCES parcela(id) ON DELETE CASCADE,
    cultivo_id     INTEGER NOT NULL REFERENCES cultivo(id) ON DELETE RESTRICT,
    fecha_siembra  TEXT    NOT NULL,
    fecha_cosecha  TEXT    NOT NULL,
    hectareas      REAL    NOT NULL CHECK (hectareas > 0),
    CHECK (fecha_cosecha > fecha_siembra)
);

CREATE INDEX IF NOT EXISTS idx_siembra_parcela ON siembra (parcela_id, fecha_siembra);
"""

# Catálogo inicial: los cultivos del Figma. (nombre, tipo, ciclo en días)
CULTIVOS = [
    ("Maíz amarillo", "cereal", 125),
    ("Frijol pinto", "leguminosa", 100),
    ("Trigo cristalino", "cereal", 130),
    ("Sorgo", "cereal", 110),
    ("Aguacate Hass", "frutal", 365),
]


def conectar() -> sqlite3.Connection:
    """Una conexión nueva. Cada petición abre y cierra la suya."""
    # check_same_thread=False: FastAPI puede crear la conexión en un hilo y usarla en otro, pero
    # cada petición usa la suya de forma secuencial, así que es seguro.
    con = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # SQLite lo trae apagado por defecto
    return con


# Versión 2: lugares para el clima. Las 4 ciudades de siempre son el punto de partida; el usuario
# puede agregar más o quitarlas. (nombre, lat, lon, zona horaria, lat y lon de un campo agrícola
# cercano para el suelo). SoilGrids no tiene dato en las zonas urbanas (el centro de la ciudad
# devuelve null) y al agricultor le sirve el suelo del campo, no el de la ciudad; esos puntos están
# verificados. Los lugares que se agreguen no traen punto de campo y se busca uno cerca.
MIGRACION_UBICACIONES = """
CREATE TABLE IF NOT EXISTS ubicacion (
    id         INTEGER PRIMARY KEY,
    nombre     TEXT NOT NULL,
    clave      TEXT NOT NULL UNIQUE,        -- clave(nombre): evita duplicados
    lat        REAL NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lon        REAL NOT NULL CHECK (lon BETWEEN -180 AND 180),
    zona       TEXT NOT NULL,               -- zona horaria IANA
    lat_suelo  REAL,
    lon_suelo  REAL
);
"""

UBICACIONES_INICIALES = [
    ("Monterrey, NL", 25.6866, -100.3161, "America/Monterrey", 25.80, -100.00),  # Pesquería
    ("Saltillo, COAH", 25.4232, -101.0053, "America/Monterrey", 25.44, -100.85),  # Arteaga
    ("Culiacán, SIN", 24.8091, -107.3940, "America/Mazatlan", 24.60, -107.55),  # valle
    ("Mérida, YUC", 20.9674, -89.5926, "America/Merida", 21.00, -89.87),  # Hunucmá
]


def iniciar() -> None:
    """Crea la base, carga la demo y aplica las migraciones pendientes. Se llama al arrancar.

    `PRAGMA user_version` guarda hasta qué versión está la base, así una base que ya tiene datos
    solo recibe lo nuevo y nunca se borra nada.
    """
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = conectar()
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            con.executescript(ESQUEMA)
            with con:  # una sola transacción: si algo falla no queda la demo a medias
                _cargar_demo(con)
                con.execute("PRAGMA user_version = 1")
        if version < 2:
            con.executescript(MIGRACION_UBICACIONES)
            with con:
                con.executemany(
                    "INSERT OR IGNORE INTO ubicacion (nombre, clave, lat, lon, zona, lat_suelo, lon_suelo)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(n, clave(n), la, lo, z, ls, lns) for n, la, lo, z, ls, lns in UBICACIONES_INICIALES],
                )
                con.execute("PRAGMA user_version = 2")
    finally:
        con.close()


def _cargar_demo(con: sqlite3.Connection) -> None:
    """Datos de ejemplo parecidos a los del Figma, con fechas relativas a hoy para que
    siempre haya cultivos en curso (se ve el carrusel de Principal y la línea de "hoy")."""
    ahora = hoy()
    d = timedelta

    con.executemany(
        "INSERT INTO cultivo (nombre, clave, tipo, ciclo_dias) VALUES (?, ?, ?, ?)",
        [(n, clave(n), t, c) for n, t, c in CULTIVOS],
    )
    cultivo = {n: i for i, n in con.execute("SELECT id, nombre FROM cultivo")}

    plan_id = con.execute("INSERT INTO plan (nombre) VALUES ('Plan principal')").lastrowid

    def parcela(nombre: str, hectareas: float) -> int:
        return con.execute(
            "INSERT INTO parcela (plan_id, nombre, clave, hectareas) VALUES (?, ?, ?, ?)",
            (plan_id, nombre, clave(nombre), hectareas),
        ).lastrowid

    def siembra(parcela_id: int, nombre: str, inicio: date, hectareas: float) -> date:
        """Inserta una siembra y devuelve su fecha de cosecha (inicio + ciclo del cultivo)."""
        ciclo = next(c for n, _, c in CULTIVOS if n == nombre)
        fin = inicio + d(days=ciclo)
        con.execute(
            "INSERT INTO siembra (parcela_id, cultivo_id, fecha_siembra, fecha_cosecha, hectareas)"
            " VALUES (?, ?, ?, ?, ?)",
            (parcela_id, cultivo[nombre], inicio.isoformat(), fin.isoformat(), hectareas),
        )
        return fin

    # La Esperanza: frijol (ya cosechado) -> maíz (en curso, día 74) -> trigo (próximo)
    esperanza = parcela("La Esperanza", 12.4)
    inicio_maiz = ahora - d(days=74)
    siembra(esperanza, "Frijol pinto", inicio_maiz - d(days=15 + 100), 8.2)
    fin_maiz = siembra(esperanza, "Maíz amarillo", inicio_maiz, 8.2)
    siembra(esperanza, "Trigo cristalino", fin_maiz + d(days=20), 8.2)

    # El Rancho: sorgo (en curso) -> frijol (próximo). Con dos parcelas en curso se ve el carrusel.
    rancho = parcela("El Rancho", 6.0)
    fin_sorgo = siembra(rancho, "Sorgo", ahora - d(days=30), 6.0)
    siembra(rancho, "Frijol pinto", fin_sorgo + d(days=15), 6.0)


def con_db():
    """Dependencia de FastAPI: una conexión por petición, que se cierra al terminar."""
    con = conectar()
    try:
        yield con
    finally:
        con.close()
