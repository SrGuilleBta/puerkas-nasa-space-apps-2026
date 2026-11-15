import { aISO } from "../utils/fechas.js";
import { leerPlanActivo } from "../utils/planActivo.js";
import { obtener } from "./cliente.js";
import { listarPlanes } from "./planificador.js";

// Noticias propias (alertas, cosechas cercanas, lluvia reciente) y titulares externos (CIMMYT, NASA).
// Devuelve { items, externasCompletas }. Usa el mismo plan que Principal (el elegido o el primero).
export async function getNoticias(municipio) {
  const planes = await listarPlanes();
  const guardado = leerPlanActivo();
  const planId = (planes.find((p) => p.id === guardado) ?? planes[0])?.id;
  return obtener("/api/noticias", { municipio, hoy: aISO(new Date()), ...(planId ? { planId } : {}) });
}
