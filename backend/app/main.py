from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.routers import cultivos, noticias, planificador, principal, suelo, ubicaciones
from app.services import catalogo_cultivos
from app.services.planificador import ErrorPlanificador


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.iniciar()  # crea la base del Planificador (con demo) si es la primera vez
    con = db.conectar()
    try:
        catalogo_cultivos.sincronizar_nombres(con)  # los nombres siguen al catálogo (p. ej. si se traduce)
    finally:
        con.close()
    yield


app = FastAPI(title="Adapting Farms with NASA Data", version="0.1.0", lifespan=lifespan)

app.include_router(principal.router)
app.include_router(planificador.router)
app.include_router(ubicaciones.router)
app.include_router(noticias.router)
app.include_router(cultivos.router)
app.include_router(suelo.router)
app.add_exception_handler(ErrorPlanificador, planificador.error_planificador)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "backend"}


# El frontend compilado (React) vive en /code/static dentro del contenedor.
# Se monta al final para que las rutas /api tengan prioridad.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
