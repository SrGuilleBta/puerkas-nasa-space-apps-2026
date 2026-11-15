from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import principal, suelo

app = FastAPI(title="Adapting Farms with NASA Data", version="0.1.0")

app.include_router(principal.router)
app.include_router(suelo.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "backend"}


# El frontend compilado (React) vive en /code/static dentro del contenedor.
# Se monta al final para que las rutas /api tengan prioridad.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
