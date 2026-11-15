// Funciones para consultar el módulo Suelo del backend (/api/suelo/...).
// `ubicacion` es { municipio } (lo normal, del selector de arriba) o { lat, lon }.

async function pedir(ruta, params) {
  const q = new URLSearchParams(params);
  const r = await fetch(`/api/suelo/${ruta}?${q}`);
  if (!r.ok) {
    let detalle = "";
    try {
      detalle = (await r.json()).detail || "";
    } catch {
      /* sin cuerpo JSON */
    }
    throw new Error(detalle || `No se pudo consultar ${ruta} (${r.status})`);
  }
  return r.json();
}

export const getActual = (ubicacion) => pedir("actual", ubicacion);
export const getEstado = (ubicacion) => pedir("estado", ubicacion);
export const getHistorico = (ubicacion, anioInicio, anioFin) =>
  pedir("historico", { ...ubicacion, anio_inicio: anioInicio, anio_fin: anioFin });
export const getPropiedades = (ubicacion) => pedir("propiedades", ubicacion);
export const getErosion = (ubicacion) => pedir("erosion", ubicacion);
export const getAguaSubterranea = (ubicacion) => pedir("agua-subterranea", ubicacion);
export const getSmap = (ubicacion) => pedir("smap", ubicacion);
export const getRaiz = (ubicacion) => pedir("raiz", ubicacion);
export const getRetencion = (ubicacion) => pedir("retencion", ubicacion);
export const getCobertura = (ubicacion) => pedir("cobertura", ubicacion);
export const getResumen = (ubicacion) => pedir("resumen", ubicacion); // para el Planificador
export const getMapa = () => pedir("mapa", {}); // mapa de todo México (NASA POWER)
// Estimación de los próximos 7 días (balance de agua con el pronóstico): humedad de raíz, temperatura del suelo, pérdida de agua
export const getProyeccion = (ubicacion) => pedir("proyeccion", ubicacion);
