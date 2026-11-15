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
export const getFicha = (cultivoId) => obtener(`${R}/cultivos/${cultivoId}/ficha`);
