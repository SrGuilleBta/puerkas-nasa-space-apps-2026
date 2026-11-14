# puerkas-nasa-space-apps-2026

NASA Space Apps Challenge 2026 — reto
[Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/).

## Stack

- **Backend:** Python 3.12 + FastAPI (`backend/`)
- **Frontend:** React 18 + Vite (`frontend/`)
- **Docker:** `docker-compose.yml` levanta los dos y los cambios se reflejan al
  guardar el archivo (sin reconstruir). El `Dockerfile` arma una sola imagen con
  todo junto, para demo o producción.

## Cómo correrlo

Requiere Docker Desktop instalado y abierto. Nada más (ni Python ni Node).

```bash
git clone https://github.com/SrGuilleBta/puerkas-nasa-space-apps-2026
cd puerkas-nasa-space-apps-2026
Start.bat
```

`Start.bat` crea el `.env` si no existe, levanta todo, espera a que responda y
abre el navegador. La primera vez tarda unos minutos (instala dependencias).
Para cambiar la llave de la API de NASA, edita `.env`.

Equivalente manual: `docker compose up -d`.

**Una sola dirección: http://localhost:8000**

| Qué | URL |
|---|---|
| App | http://localhost:8000 |
| Docs de la API | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

Guardas un archivo del backend o del frontend y se ve el cambio solo. Solo si
agregas una librería (`requirements.txt` o `package.json`) hay que reiniciar:

```bash
docker compose up -d --force-recreate
```

Logs: `docker compose logs -f` · Apagar: `docker compose down`.


## Documentación

| Qué | Dónde |
|---|---|
| Qué hará cada pantalla (según el Figma) y qué datos necesita | [docs/funcionalidades.md](docs/funcionalidades.md) |
| Cómo organizar el código y agregar un módulo (con ejemplo completo) | [docs/estructura.md](docs/estructura.md) |
| Qué datos usa cada pantalla y de dónde salen | [docs/datos.md](docs/datos.md) ([versión CSV](docs/datos.csv)) |
| Los CSV de SIAP: formato y cómo descargar otros años | [backend/data/siap/README.md](backend/data/siap/README.md) |

Resumen para empezar a programar:

1. `Start.bat` y abrir http://localhost:8000.
2. Elegir **un módulo** (Clima, Suelo, Mercado, Cultivos...) y trabajar solo en sus archivos.
3. Guardar el archivo: el cambio se ve solo, sin reiniciar.

### RECURSOS DE EQUIPO:

- Excel Recursos x Modulo: https://docs.google.com/spreadsheets/d/1HQcgaiH6-ikuGKZWbB0F6XbkSEmYJTXf9zZksEYQKdY/edit?usp=sharing
- Figma: https://www.figma.com/make/u0K7IcKBPNddczAZhtR4ic/Dise%C3%B1ar-Dashboard-Agr%C3%ADcola-Org%C3%A1nico?t=PF9eQYg05PTj8hxM-1

