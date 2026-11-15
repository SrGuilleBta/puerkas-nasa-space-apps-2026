# ---- Etapa 1: compilar el frontend (React + Vite) ----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Etapa 2: pipeline de Cultivos (genera backend/data/cultivos) ----
FROM python:3.12-slim AS datos
WORKDIR /code
COPY backend/pipeline/requirements.txt pipeline/requirements.txt
RUN pip install --no-cache-dir -r pipeline/requirements.txt
COPY backend/data ./data
COPY backend/pipeline ./pipeline
RUN python -m pipeline.cultivos

# ---- Etapa 3: backend Python que también sirve el frontend compilado ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Datasets locales (SIAP, etc.); el código los lee desde /code/data
COPY backend/data ./data
COPY --from=datos /code/data/cultivos ./data/cultivos
COPY --from=frontend /frontend/dist ./static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
