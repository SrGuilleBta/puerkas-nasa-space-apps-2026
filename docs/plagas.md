# Motor de plagas

Dice, para un cultivo del catálogo y una ubicación, qué plagas y enfermedades lo pueden afectar y si el clima de
estos días las favorece. Sale en la pestaña **Crop guide** del popup de cada siembra, al final y cerrada por defecto
(sección "Pests and diseases": la cabecera resume "4 critical · 8 high" y al abrirla salen las plagas),
alimenta los avisos de **Principal** y las noticias propias de **Noticias**.

Son avisos para revisar el campo: nada de esto detecta una plaga en la parcela.

## Cómo calcula

1. **Plagas del cultivo.** Con el `eppocode` del cultivo (lo trae el catálogo de Cultivos) pide a EPPO
   (`taxons/taxon/{código}/pests`) las plagas asociadas y se queda con las que están en México
   (`backend/data/plagas/plagas_mx.json`, bajado de EPPO; se omiten las ausentes y las erradicadas).
2. **Cuáles analiza.** Las más extendidas en el país primero (estado A, B, C...) y hasta `LIMITE_PLAGAS` (12) por cultivo.
   Las malezas se omiten: el clima no dice nada de ellas.
3. **Expediente de cada plaga** (EPPO, 8 endpoints): nombres, tipo biológico, hospederos, vectores, control
   biológico, estatus de cuarentena y fotos.
4. **Clima.** Serie diaria de Open-Meteo: 3 días pasados y 7 de pronóstico (temperatura máxima, mínima y media,
   humedad media y probabilidad de lluvia; en los días pasados la lluvia sale de lo medido).
5. **Registros cercanos.** GBIF e iNaturalist, en un radio de 100 km.
6. **Riesgo** (`services/plagas/evaluar.py`):

| Tipo | Día favorable | Clima favorable (`high`) | Parcialmente favorable (`medium`) |
|---|---|---|---|
| Insecto, ácaro, bacteria o virus | máxima de 18 a 35 °C y humedad de 40 % o más | 65 grados-día o más (media menos 10 °C) | 45 o más |
| Hongo | media de 12 a 26 °C y humedad de 80 % o más (o 50 % o más de lluvia) | 3 días seguidos | 2 días seguidos |

Con clima favorable el riesgo es `high`; sube a `critical` si hay registros de la plaga a menos de 100 km. Lo demás
es `medium` o `low`. No tener registros cerca no descarta nada: depende de que alguien los suba.

## Dónde corre y qué guarda

- **Segundo plano.** El primer análisis de un cultivo tarda (decenas de consultas). `GET
  /api/planificador/catalogo/{id}/plagas?municipio=` responde de inmediato con `estado`: `listo`, `calculando` (la
  pantalla vuelve a preguntar cada 3 s), `error` o `no_disponible` (con `mensaje`).
- **Caché en memoria:** el resultado, 6 horas por código EPPO y lugar (dos cultivos con el mismo código, como los
  dos maíces, comparten análisis). Tras un error se espera 5 minutos para reintentar.
- **Caché en disco** (`backend/data/plagas/cache`, fuera de git): plagas de un cultivo 30 días, expediente de una
  plaga 60 días y registros cercanos 7 días. Un fallo de EPPO, GBIF o iNaturalist no se guarda: nunca se cachea un
  "sin registros" que no es cierto. Se puede borrar la carpeta sin riesgo.

## Alertas y noticias

`services/alertas.py` recibe los resultados vigentes (`plagas.para_alertas`) y, por cada cultivo en curso con
plagas de riesgo `critical`, crea un aviso de nivel alto que nombra hasta 3 de ellas. Las de riesgo `high`, `medium`
y `low` no avisan: están en la guía del cultivo. Un cultivo con análisis y sin plagas críticas no recibe aviso de
plagas, ni siquiera de las reglas generales. Los cultivos que aún no tienen análisis (primera vez, sin código EPPO,
sin llave o con EPPO caído) siguen con las reglas generales por tipo de cultivo. Noticias muestra esos mismos avisos.

Por qué solo las críticas: con los umbrales actuales casi todas las plagas salen en riesgo alto casi todo el año
(en una prueba en Monterrey, en noviembre, 12 de 12 plagas de maíz, 12 de 12 de frijol y 12 de 12 de aguacate
quedaron en `high` o `critical`). Avisar de todas haría que el aviso no sirviera.

La primera vez que se abre Principal con un cultivo nuevo todavía no hay análisis: el motor arranca en segundo
plano y los avisos del motor aparecen en la siguiente consulta.

## Configuración

`EPPO_API_KEY` en `.env` (ver `.env.example`; la llave se pide en <https://data.eppo.int/>). Sin ella el motor
responde `no_disponible` y todo sigue con las reglas generales. El código no trae ninguna llave escrita.

Docker lee el `.env` solo al crear el contenedor: después de agregar la llave hay que recrear el backend
(`docker compose up -d --force-recreate backend`). Si la pantalla dice "The pest engine needs EPPO_API_KEY in .env",
es porque el contenedor sigue con la configuración vieja.

## Pendiente

- **Calibrar los umbrales** (`services/plagas/evaluar.py`; constantes `GDD_BASE`, `GDD_ALTO`, `GDD_MEDIO` y los rangos de
  temperatura y humedad de `evaluar_clima`). Son umbrales generales del motor original, iguales para todas las
  plagas. Un insecto sube a riesgo alto con 65 grados-día en 10 días, es decir, con temperatura media sobre 16.5 °C,
  algo que en buena parte de México pasa casi todo el año. Hace falta criterio agronómico por plaga (o por grupo) de
  quien armó el motor: temperatura mínima y máxima de desarrollo, grados-día de una generación y humedad que necesita.
  Mientras tanto el aviso solo sale con plagas críticas. Si se calibran, revisar si conviene volver a avisar las de
  riesgo alto (`_del_motor_de_plagas` en `services/alertas.py`).
- Los nematodos del suelo, los virus y las bacterias se evalúan con la temperatura del aire (como los insectos); el
  suelo y los vectores no entran. Es una aproximación del motor original.
- Dos subespecies del mismo insecto (p. ej. *Diabrotica undecimpunctata*) salen como dos plagas con los mismos
  registros cercanos, porque GBIF e iNaturalist se buscan por especie.
- Dosis, productos y manejo químico: el motor no los da a propósito (solo control biológico de EPPO). El manejo
  por estado sale de las agendas del INIFAP en la misma pestaña.
