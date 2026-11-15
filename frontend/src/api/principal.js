// Datos de la pantalla Principal: una función por sección.
//
// Hoy todas devuelven el ejemplo de datosEjemplo.js. Para conectar una sección con datos
// reales se cambia SOLO su función, por ejemplo:
//
//   export const getClima = (municipio) => obtener("/api/principal/clima", { municipio });
//
// La pantalla no cambia mientras la forma del objeto devuelto sea la misma.
import { aISO } from "../utils/fechas.js";
import { leerPlanActivo } from "../utils/planActivo.js";
import { obtener } from "./cliente.js";
import * as ejemplo from "./datosEjemplo.js";
import { getPlan, listarPlanes } from "./planificador.js";

// Simula una consulta al backend. Se borra cuando la sección deje de usar el ejemplo.
const simular = (datos) => Promise.resolve(datos);

export const getParcela = () => simular(ejemplo.parcela);

// Alertas reales: riesgos del clima y condiciones favorables para plagas según los cultivos en curso.
export const getAlertas = (municipio, planId) =>
  obtener("/api/principal/alertas", { municipio, hoy: aISO(new Date()), ...(planId ? { planId } : {}) });

// Clima real (Meteomatics, vía el backend). `esEjemplo` controla la insignia de la tarjeta.
// El pH del suelo viene como null hasta que se conecte SoilGrids.
export const getClima = async (municipio) => {
  const { pronostico, hoy } = await obtener("/api/principal/clima", { municipio });
  return { pronostico, hoy, esEjemplo: false };
};

export const getAlertaRegional = (municipio) => simular(ejemplo.alertaRegional);

// Lo que viene del Planificador: el plan que se está viendo (el elegido allá o el primero) y sus
// siembras en curso hoy. Alimenta las tarjetas "Cultivos activos" y "Plan anual".
// Devuelve { plan: null, activos: [] } si todavía no hay ningún plan.
export async function getPlanificacion() {
  const planes = await listarPlanes();
  const guardado = leerPlanActivo();
  const planId = (planes.find((p) => p.id === guardado) ?? planes[0])?.id ?? null;
  if (planId === null) return { plan: null, activos: [] };
  const [plan, activos] = await Promise.all([
    getPlan(planId),
    obtener("/api/principal/cultivos-activos", { planId, hoy: aISO(new Date()) }),
  ]);
  return { plan, activos };
}

// Lo que pasó en el campo en un periodo (lluvia, temperatura, radiación y humedad de la raíz), NASA POWER.
export const getClimaNasa = (municipio, desde, hasta) =>
  obtener("/api/principal/clima-nasa", { municipio, desde: aISO(desde), hasta: aISO(hasta) });
