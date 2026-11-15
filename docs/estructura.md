# Cómo estructurar el código

Guía para que backend y frontend crezcan ordenados y no nos pisemos los archivos. La estructura sigue
las pantallas del Figma (Principal, Clima, Mercado, Cultivos, Planificador y Noticias). Qué hace cada
una está en [funcionalidades.md](funcionalidades.md). Si cambian las pantallas, se ajustan los nombres
de las páginas y la forma de organizar no cambia.

Los datos que usa cada módulo están en [datos.md](datos.md).

## Idea general

```
Navegador (React)  ──/api/...──▶  FastAPI  ──▶  fuentes de datos
                                     │            (Meteomatics, SoilGrids, NASA POWER...)
                                     └──────────▶  SQLite y archivos locales (backend/data)
```

- **El frontend nunca llama a APIs externas.** Todo pasa por el backend (`/api/...`). Así las llaves
  quedan en el servidor, no hay problemas de CORS y se puede guardar en caché.
- **Un módulo = un router + un servicio + una página.** Cada persona trabaja en su módulo y casi no
  toca los mismos archivos.
- Con `docker-compose.yml` corren dos contenedores (backend y frontend), pero se entra por **una sola
  dirección**: http://localhost:8000. El frontend reenvía `/api` y `/docs` al backend.

## Árbol de carpetas

Así está hoy el repo. `[pendiente]` = lo pone el módulo que falta (Clima, Mercado, Cultivos, Noticias).
Git no guarda carpetas vacías: una carpeta nueva aparece en el repo en cuanto tenga su primer archivo.

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              crea la app, registra routers, monta el frontend
│   │   ├── config.py            variables de entorno (Meteomatics) y ruta de la base
│   │   ├── db.py                SQLite: esquema, migraciones (PRAGMA user_version) y datos de inicio
│   │   ├── routers/             rutas HTTP; un archivo por módulo, sin lógica pesada
│   │   │   ├── principal.py     clima, alertas y cultivos activos de Principal
│   │   │   ├── planificador.py  planes, parcelas, siembras, resumen y recomendaciones
│   │   │   ├── ubicaciones.py   lugares guardados, búsqueda por nombre y "Mi ubicación"
│   │   │   ├── clima.py         [pendiente]
│   │   │   ├── mercado.py       [pendiente]
│   │   │   ├── cultivos.py      [pendiente]
│   │   │   └── noticias.py      [pendiente]
│   │   ├── services/            lógica y clientes de datos; no importan FastAPI
│   │   │   ├── meteomatics.py   pronóstico y condiciones de hoy (caché de 10 min)
│   │   │   ├── soilgrids.py     pH del suelo (caché de 24 h, busca puntos vecinos)
│   │   │   ├── alertas.py       reglas de clima, plagas y enfermedades
│   │   │   ├── planificador.py  reglas del plan (sin traslapes, rotación, resumen)
│   │   │   ├── ubicaciones.py   lugares guardados y geocodificación (solo México)
│   │   │   ├── nasa_power.py    clima observado por satélite (lluvia, temperatura, radiación, humedad de raíz)
│   │   │   ├── siap.py          [pendiente] leerá los CSV de backend/data/siap
│   │   │   └── ecocrop.py       [pendiente]
│   │   └── schemas/             modelos Pydantic de las respuestas (camelCase hacia el frontend)
│   ├── data/
│   │   ├── siap/                CSV 2015-2025 y su README
│   │   └── planificador.db      base SQLite (se crea sola; no se sube a git)
│   ├── tests/                   unittest: `python -m unittest discover -s tests`
│   └── requirements.txt
├── frontend/
│   ├── index.html, vite.config.js
│   └── src/
│       ├── main.jsx, App.jsx    punto de entrada; ubicación activa, layout y rutas
│       ├── routes.js            rutas con hash (#/clima, #/planificador)
│       ├── api/                 una función por consulta al backend
│       │   ├── cliente.js       fetch común con manejo de errores
│       │   ├── principal.js, planificador.js, ubicaciones.js
│       │   └── datosEjemplo.js  datos de ejemplo de lo que aún no tiene backend
│       ├── pages/               una carpeta por pantalla
│       │   ├── Principal/       banner de alertas, pronóstico, cultivos activos, plan anual
│       │   ├── Planificador/    calendario, barra de tiempo, popups, resumen, recomendaciones
│       │   ├── Clima/, Mercado/, Cultivos/, Noticias/   [pendiente]
│       ├── components/          Layout, Dialogo, Cargable, SelectorUbicacion, Iconos...
│       ├── hooks/               useDatos (cargando / error / recargar)
│       ├── utils/               fechas, ventana de tiempo, colores, plan activo
│       └── styles/              global.css con los colores y medidas
├── docs/                        documentación (datos.md, funcionalidades.md, este archivo)
├── Dockerfile, docker-compose.yml, Start.bat, .env.example
└── README.md
```

Las carpetas de Python no traen `__init__.py`: en Python 3 no es obligatorio. Si algún `import` no
encuentra una carpeta, crea un `__init__.py` vacío dentro.

## Qué va en cada capa

| Capa | Qué hace | Qué NO hace |
|---|---|---|
| `routers/` | Define la ruta, valida parámetros (`lat`, `lon`, fechas) y llama a un servicio | Consultar APIs ni leer archivos |
| `services/` | Pide datos a la fuente, los limpia y devuelve datos simples | Importar FastAPI ni conocer rutas |
| `data/` | Archivos locales (CSV) | Código |
| `api/` (frontend) | `fetch` a `/api/...` y devuelve JSON | Dibujar nada |
| `pages/` | Una pantalla: junta datos y componentes | Hacer `fetch` directo (usa `api/`) |
| `components/` | Piezas visuales sin saber de dónde vienen los datos | Llamar al backend |

## Nombres

- Módulos del dominio en español y sin acentos en archivos: `clima.py`, `linea_tiempo.py`.
- Python: `snake_case`. Componentes React: `PascalCase` (`TarjetaClima.jsx`). Funciones y variables JS: `camelCase`.
- Rutas de la API: `/api/<modulo>/<accion>`, por ejemplo `/api/clima/historico`.
- Un componente por archivo, y su CSS junto a él si lo necesita.

## Cómo agregar un módulo (ejemplo con Clima)

**1. Servicio**: `backend/app/services/nasa_power.py`

```python
import httpx

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


async def diario(lat: float, lon: float, inicio: str, fin: str) -> dict:
    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR",
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": inicio,  # AAAAMMDD
        "end": fin,
        "format": "JSON",
    }
    async with httpx.AsyncClient(timeout=30) as cliente:
        r = await cliente.get(URL, params=params)
        r.raise_for_status()
        return r.json()["properties"]["parameter"]
```

**2. Router**: `backend/app/routers/clima.py`

```python
from fastapi import APIRouter

from app.services import nasa_power

router = APIRouter(prefix="/api/clima", tags=["clima"])


@router.get("/historico")
async def historico(lat: float, lon: float, inicio: str, fin: str):
    return await nasa_power.diario(lat, lon, inicio, fin)
```

**3. Registrarlo en `backend/app/main.py`**, **antes** del `app.mount("/", ...)` (el mount del
frontend va al final porque atrapa todo lo demás):

```python
from app.routers import clima

app.include_router(clima.router)
```

**4. Función del frontend**: `frontend/src/api/clima.js`

```js
export async function getHistorico(lat, lon, inicio, fin) {
  const q = new URLSearchParams({ lat, lon, inicio, fin });
  const r = await fetch(`/api/clima/historico?${q}`);
  if (!r.ok) throw new Error("No se pudo consultar el clima");
  return r.json();
}
```

**5. Página**: `frontend/src/pages/Clima/Clima.jsx` llama a `getHistorico` y pinta los datos con
componentes de `components/`.

## Detalles que ya sabemos que dan problemas

1. **Rutas del frontend.** Con `docker-compose.yml` refrescar en `/clima` funciona. Pero la imagen del
   `Dockerfile` (demo/producción) responde `404` en cualquier ruta que no sea `/`: lo probé. Si usan
   `react-router-dom` (hay que instalarlo, no viene en el `package.json`), usen **`HashRouter`**
   (`/#/clima`) para que funcione en los dos; con `BrowserRouter` habría que añadir en `main.py` una
   ruta de respaldo que devuelva `index.html`.
2. **Valores `-999` de NASA POWER** significan "sin dato". Conviértanlos a `null` en el servicio.
3. **CSV de SIAP**: están en ISO-8859-1 y 2015–2020 usan otros nombres en dos columnas. Todo está
   explicado en [backend/data/siap/README.md](../backend/data/siap/README.md); resuélvanlo una sola
   vez en `services/siap.py` y que el resto del código no se entere.
4. **Caché**: SoilGrids y POWER son lentos. Guarden la respuesta en memoria por (lat, lon, fechas)
   dentro del servicio para no repetir la consulta.
5. **Llaves y variables de entorno**: se declaran en `.env.example`, se leen en `config.py` y se pasan
   al contenedor en `docker-compose.yml`. Nunca en el código ni en el commit.

## Cómo trabajar a diario

| Quiero... | Hago |
|---|---|
Una sola dirección para todo: **http://localhost:8000**

| Quiero... | Hago |
|---|---|
| Levantar todo | `Start.bat` (o `docker compose up -d`) |
| Ver un cambio (backend o frontend) | Guardar el archivo. Se refleja solo, sin reiniciar |
| Agregar una librería | Ponerla en `backend/requirements.txt` o `frontend/package.json` y `docker compose up -d --force-recreate` |
| Probar un endpoint | http://localhost:8000/docs |
| Ver logs | `docker compose logs -f` |
| Apagar | `docker compose down` |

## Para no chocar en git

- Una rama por persona o por módulo, y se junta cuando funciona.
- Los únicos archivos que varias personas tocan seguido son `backend/app/main.py` (una línea por
  router) y `frontend/src/App.jsx` (una ruta por página). Manténganlos cortos y cambien solo su línea.
- Los CSV grandes de `backend/data/` no se editan a mano; si hay que actualizarlos, se vuelven a
  descargar con el comando del README de esa carpeta.
