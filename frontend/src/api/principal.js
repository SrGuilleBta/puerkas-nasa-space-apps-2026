// Datos de la pantalla Principal: una función por sección, todas con datos reales del backend.
import { aISO } from "../utils/fechas.js";
import { leerPlanActivo } from "../utils/planActivo.js";
import { obtener } from "./cliente.js";
import { getPlan, listarPlanes } from "./planificador.js";

// Alertas reales: riesgos del clima y condiciones favorables para plagas según los cultivos en curso.
export const getAlertas = (municipio, planId) =>
  obtener("/api/principal/alertas", { municipio, hoy: aISO(new Date()), ...(planId ? { planId } : {}) });

// Tareas del Planificador sin hacer cuya fecha ya pasó: { total, tareas } con las más atrasadas.
// No depende del clima, así que se muestran aunque falle el pronóstico.
export const getTareasVencidas = (planId) =>
  obtener("/api/principal/tareas-vencidas", { hoy: aISO(new Date()), ...(planId ? { planId } : {}) });

// Clima real (Meteomatics o, si no hay llaves, Open-Meteo: `fuente` dice cuál); el pH y la humedad del suelo
// los agrega el módulo Suelo.
export const getClima = async (municipio) => {
  const { pronostico, hoy, fuente } = await obtener("/api/principal/clima", { municipio });
  return { pronostico, hoy, fuente };
};

// Lo que viene del Planificador: el plan que se está viendo (el elegido allá o el primero) y sus
// siembras en curso hoy. Alimenta las tarjetas "Cultivos activos" y "Plan anual".
// `municipio` (la ubicación activa) elige el estado de donde salen el precio y el rendimiento de SIAP.
// Devuelve { plan: null, activos: [] } si todavía no hay ningún plan.
export async function getPlanificacion(municipio) {
  const planes = await listarPlanes();
  const guardado = leerPlanActivo();
  const planId = (planes.find((p) => p.id === guardado) ?? planes[0])?.id ?? null;
  if (planId === null) return { plan: null, activos: [] };
  const [plan, activos] = await Promise.all([
    getPlan(planId),
    obtener("/api/principal/cultivos-activos", { planId, hoy: aISO(new Date()), ...(municipio ? { municipio } : {}) }),
  ]);
  return { plan, activos };
}

// Lo que pasó en el campo en un periodo (lluvia, temperatura, radiación y humedad de la raíz), NASA POWER.
export const getClimaNasa = (municipio, desde, hasta) =>
  obtener("/api/principal/clima-nasa", { municipio, desde: aISO(desde), hasta: aISO(hasta) });
