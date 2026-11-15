// Enciclopedia de cultivos: los datos los precalcula la pipeline del backend (ver docs/cultivos-pipeline.md).
import { obtener } from "./cliente.js";

const R = "/api/cultivos";

// Estados y municipios para el filtro de zona.
// -> { estados: [{ clave, nombre, municipios: [{ clave, nombre, con_datos }] }] }
export const getZonas = () => obtener(`${R}/ubicaciones`);

// Todos los cultivos del catálogo (ligero). Con `clave` (estado o municipio) llegan ordenados por
// superficie sembrada ahí y marcados con `sembrado_en_ubicacion`. La búsqueda y los filtros
// se hacen en el navegador para que respondan al teclear.
export const getBiblioteca = (clave) => obtener(`${R}/biblioteca`, clave ? { clave } : {});

// Ficha completa de un cultivo en una zona. `clave` vacío = todo México.
// Si el municipio no siembra el cultivo, el backend responde con los datos del estado o del país
// y lo indica en `nivel_datos` y `sembrado_en_ubicacion`.
export const getFicha = (clave, cultivo) => obtener(`${R}/viabilidad`, { clave: clave || "00", cultivo });

// Zona de SIAP (municipio o, si no hay correspondencia, estado) de una ubicación del proyecto:
// -> { clave, nivel, nombre, estado, cve_ent } o null si no se puede determinar.
export const getZonaDeUbicacion = ({ nombre, lat, lon }) => obtener(`${R}/zona`, { nombre, lat, lon });
