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

# ---- Etapa 3: precios de Mercado (genera backend/data/mercado desde market_data) ----
FROM python:3.12-slim AS mercado
WORKDIR /mercado
COPY backend/pipeline/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# exportar_json.py busca market_data junto a su carpeta (RAIZ = carpeta padre del script)
COPY market_data ./market_data
COPY market_scripts ./market_scripts
RUN MERCADO_SALIDA=/mercado/salida python market_scripts/exportar_json.py

# ---- Etapa 4: backend Python que también sirve el frontend compilado ----
FROM python:3.12-slim

# La imagen sale en modo solo lectura (demo pública: nadie puede crear, editar ni borrar planes).
# Para usarla como app normal: docker run -e SOLO_LECTURA=0 ...
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOLO_LECTURA=1

WORKDIR /code

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Datasets locales (SIAP, etc.); el código los lee desde /code/data
COPY backend/data ./data
COPY --from=datos /code/data/cultivos ./data/cultivos
COPY --from=mercado /mercado/salida ./data/mercado
COPY --from=frontend /frontend/dist ./static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
