# puerkas-nasa-space-apps-2026

NASA Space Apps Challenge 2026 — reto
[Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/).

## Stack

- **Backend:** Python 3.12 + FastAPI (`backend/`)
- **Frontend:** React 18 + Vite (`frontend/`)
- **Contenedor:** uno solo. El `Dockerfile` compila el frontend y FastAPI lo
  sirve junto con la API.

## Cómo correrlo

Requiere Docker Desktop instalado y abierto. Nada más (ni Python ni Node).

```bash
git clone https://github.com/SrGuilleBta/puerkas-nasa-space-apps-2026
cd puerkas-nasa-space-apps-2026
Start.bat
```

`Start.bat` crea el `.env` si no existe, construye y levanta el contenedor,
espera a que responda y abre el navegador. La primera vez tarda unos minutos.
Para cambiar la llave de la API de NASA, edita `.env`.

Equivalente manual: `docker compose up --build -d`.

| Qué | URL |
|---|---|
| App (frontend + API) | http://localhost:8000 |
| Docs de la API | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

El contenedor se llama `puerkas`. Después de cambiar código (backend o
frontend) hay que reconstruirlo:

```bash
docker compose up --build -d
```

Logs: `docker logs -f puerkas` · Apagar: `docker compose down`.

## Desarrollo con recarga en vivo (opcional)

Para ver cambios del frontend al instante, fuera de Docker:

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

El proxy de Vite manda `/api` al backend en `localhost:8000`.
