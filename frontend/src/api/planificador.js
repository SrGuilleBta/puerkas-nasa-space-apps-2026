// API del Planificador (planes, parcelas, siembras y catálogo de cultivos).
// Los errores llegan como ErrorApi con un `mensaje` listo para mostrar.
import { aISO } from "../utils/fechas.js";
import { enviar, obtener } from "./cliente.js";

const R = "/api/planificador";

// Planes
export const listarPlanes = () => obtener(`${R}/planes`);
export const getPlan = (id) => obtener(`${R}/planes/${id}`);
// Resumen del ciclo y qué sembrar después en cada parcela. `hoy` es la fecha local del navegador.
export const getAnalisis = (id) => obtener(`${R}/planes/${id}/analisis`, { hoy: aISO(new Date()) });
export const crearPlan = (nombre) => enviar("POST", `${R}/planes`, { nombre });
export const renombrarPlan = (id, nombre) => enviar("PATCH", `${R}/planes/${id}`, { nombre });
export const borrarPlan = (id) => enviar("DELETE", `${R}/planes/${id}`);

// Parcelas: datos = { nombre, hectareas }
export const crearParcela = (planId, datos) => enviar("POST", `${R}/planes/${planId}/parcelas`, datos);
export const editarParcela = (id, datos) => enviar("PATCH", `${R}/parcelas/${id}`, datos);
export const borrarParcela = (id) => enviar("DELETE", `${R}/parcelas/${id}`);

// Catálogo de cultivos: datos = { nombre, tipo, cicloDias }
export const listarCultivos = () => obtener(`${R}/cultivos`);
export const crearCultivo = (datos) => enviar("POST", `${R}/cultivos`, datos);

// Siembras: datos = { cultivoId, fechaSiembra, fechaCosecha?, hectareas? } (fechas AAAA-MM-DD)
export const crearSiembra = (parcelaId, datos) => enviar("POST", `${R}/parcelas/${parcelaId}/siembras`, datos);
export const editarSiembra = (id, datos) => enviar("PATCH", `${R}/siembras/${id}`, datos);
export const borrarSiembra = (id) => enviar("DELETE", `${R}/siembras/${id}`);

// Catálogo de Cultivos: lista para elegir, cultivo del Planificador a partir de uno del catálogo y su ficha.
export const getCatalogo = () => obtener(`${R}/catalogo`);
export const cultivoDesdeCatalogo = (catalogoId) => enviar("POST", `${R}/cultivos/desde-catalogo`, { catalogoId });
// `municipio` (el nombre de la ubicación activa) sirve para traer el manejo del INIFAP de su estado.
const conMunicipio = (municipio) => (municipio ? { municipio } : {});
export const getFicha = (cultivoId, municipio) => obtener(`${R}/cultivos/${cultivoId}/ficha`, conMunicipio(municipio));
export const getFichaCatalogo = (catalogoId, municipio) =>
  obtener(`${R}/catalogo/${catalogoId}/ficha`, conMunicipio(municipio));

// Mejor época para sembrar un cultivo del catálogo en una ubicación (NASA POWER + temperatura ideal).
export const getVentanaSiembra = (catalogoId, municipio) =>
  obtener(`${R}/catalogo/${catalogoId}/ventana-siembra`, { municipio });

// Tareas de una siembra (fertilizar, regar, cosechar...) con marca de hecha.
export const listarTareas = (siembraId) => obtener(`${R}/siembras/${siembraId}/tareas`);
export const crearTarea = (siembraId, datos) => enviar("POST", `${R}/siembras/${siembraId}/tareas`, datos);
export const tareasSugeridas = (siembraId) => enviar("POST", `${R}/siembras/${siembraId}/tareas/sugeridas`, {});
export const editarTarea = (id, cambios) => enviar("PATCH", `${R}/tareas/${id}`, cambios);
export const borrarTarea = (id) => enviar("DELETE", `${R}/tareas/${id}`);

// Copiar el plan a otro año ({ nombre, anios }) y descargarlo en CSV o en PDF.
export const duplicarPlan = (id, datos) => enviar("POST", `${R}/planes/${id}/duplicar`, datos);
export const urlExportarPlan = (id) => `${R}/planes/${id}/exportar`;
// El PDF lleva la fecha local del navegador para calcular "hoy" (uso del suelo, próxima cosecha).
export const urlExportarPlanPdf = (id) => `${R}/planes/${id}/exportar-pdf?hoy=${aISO(new Date())}`;
