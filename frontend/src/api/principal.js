// Datos de la pantalla Principal: una función por sección.
//
// Hoy todas devuelven el ejemplo de datosEjemplo.js. Para conectar una sección con datos
// reales se cambia SOLO su función, por ejemplo:
//
//   export const getClima = (municipio) => obtener("/api/principal/clima", { municipio });
//
// La pantalla no cambia mientras la forma del objeto devuelto sea la misma.
import { obtener } from "./cliente.js";
import * as ejemplo from "./datosEjemplo.js";

// Simula una consulta al backend. Se borra cuando la sección deje de usar el ejemplo.
const simular = (datos) => Promise.resolve(datos);

export const getParcela = () => simular(ejemplo.parcela);

export const getAviso = (municipio) => simular(ejemplo.aviso);

// Clima real (Meteomatics, vía el backend). `esEjemplo` controla la insignia de la tarjeta.
// El pH del suelo viene como null hasta que se conecte SoilGrids.
export const getClima = async (municipio) => {
  const { pronostico, hoy } = await obtener("/api/principal/clima", { municipio });
  return { pronostico, hoy, esEjemplo: false };
};

export const getAlertaRegional = (municipio) => simular(ejemplo.alertaRegional);

export const getCultivoActivo = (municipio) => simular(ejemplo.cultivoActivo);

export const getPlanAnual = () => simular(ejemplo.planAnual);
