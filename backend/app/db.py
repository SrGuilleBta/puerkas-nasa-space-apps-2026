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

VERSION_ESQUEMA = 5  # versión actual de la base (ver iniciar)

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
        if version < 3:
            with con:
                _renombrar_mi_ubicacion(con)
                con.execute("PRAGMA user_version = 3")
        if version < 4:
            _enlazar_catalogo(con)
        if version < 5:
            _agregar_economia_tareas_y_estado(con)
    finally:
        con.close()


# Cultivos de demo -> cultivo del catálogo de Cultivos (nombre viejo, nombre nuevo, id del catálogo)
DEMO_A_CATALOGO = [
    ("Maíz amarillo", "Maíz grano", "maiz-grano"),
    ("Frijol pinto", "Frijol", "frijol"),
    ("Trigo cristalino", "Trigo grano", "trigo-grano"),
    ("Sorgo", "Sorgo grano", "sorgo-grano"),
    ("Aguacate Hass", "Aguacate", "aguacate"),
]


def _enlazar_catalogo(con: sqlite3.Connection) -> None:
    """Versión 4: cada cultivo puede venir del catálogo de Cultivos (columna `catalogo_id`).

    Los cultivos de demo se renombran al nombre del catálogo y se enlazan, así tienen ficha. Solo si
    la fila conserva exactamente el nombre de demo y el nombre nuevo no está ya tomado; los cultivos
    que creó el usuario no se tocan.
    """
    with con:
        con.execute("ALTER TABLE cultivo ADD COLUMN catalogo_id TEXT")
        for viejo, nuevo, id_catalogo in DEMO_A_CATALOGO:
            if con.execute("SELECT 1 FROM cultivo WHERE clave = ?", (clave(nuevo),)).fetchone():
                continue
            con.execute(
                "UPDATE cultivo SET nombre = ?, clave = ?, catalogo_id = ? WHERE nombre = ?",
                (nuevo, clave(nuevo), id_catalogo, viejo),
            )
        con.execute("PRAGMA user_version = 4")


# Estado (clave INEGI) de las 4 ciudades de inicio, para las agendas técnicas del INIFAP
ESTADO_DE_INICIO = {"monterrey, nl": "19", "saltillo, coah": "05", "culiacan, sin": "25", "merida, yuc": "31"}


def _agregar_economia_tareas_y_estado(con: sqlite3.Connection) -> None:
    """Versión 5: costos e ingresos por siembra, tareas por siembra y estado de cada ubicación.

    - `siembra` gana rendimiento (t/ha), precio ($/t) y costo ($/ha): opcionales, los captura el usuario.
    - `tarea`: actividades de una siembra (fertilizar, regar...) con marca de hecha. Se borran con la siembra.
    - `ubicacion.cve_ent`: estado (clave INEGI de 2 dígitos) para mostrar el manejo del INIFAP de ese estado.
    """
    with con:
        con.execute("ALTER TABLE siembra ADD COLUMN rendimiento_t_ha REAL CHECK (rendimiento_t_ha IS NULL OR rendimiento_t_ha >= 0)")
        con.execute("ALTER TABLE siembra ADD COLUMN precio_t REAL CHECK (precio_t IS NULL OR precio_t >= 0)")
        con.execute("ALTER TABLE siembra ADD COLUMN costo_ha REAL CHECK (costo_ha IS NULL OR costo_ha >= 0)")
        con.execute(
            """CREATE TABLE IF NOT EXISTS tarea (
                id         INTEGER PRIMARY KEY,
                siembra_id INTEGER NOT NULL REFERENCES siembra(id) ON DELETE CASCADE,
                titulo     TEXT    NOT NULL,
                tipo       TEXT    NOT NULL DEFAULT 'other',
                fecha      TEXT    NOT NULL,
                hecha      INTEGER NOT NULL DEFAULT 0 CHECK (hecha IN (0, 1))
            )"""
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_tarea_siembra ON tarea (siembra_id, fecha)")
        con.execute("ALTER TABLE ubicacion ADD COLUMN cve_ent TEXT")
        for nombre_clave, estado in ESTADO_DE_INICIO.items():
            con.execute("UPDATE ubicacion SET cve_ent = ? WHERE clave = ?", (estado, nombre_clave))
        con.execute("PRAGMA user_version = 5")


def _renombrar_mi_ubicacion(con: sqlite3.Connection) -> None:
    """Versión 3: la interfaz pasó a inglés, así que "Mi ubicación" (texto de la interfaz) pasa a
    "My location". Solo si la fila conserva exactamente el nombre viejo y no hay ya una con el nuevo."""
    nuevo = "My location"
    if con.execute("SELECT 1 FROM ubicacion WHERE clave = ?", (clave(nuevo),)).fetchone():
        return
    con.execute(
        "UPDATE ubicacion SET nombre = ?, clave = ? WHERE nombre = 'Mi ubicación'",
        (nuevo, clave(nuevo)),
    )


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
