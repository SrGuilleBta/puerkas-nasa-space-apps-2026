// Datos de la pantalla Principal: una función por sección.
//
// Hoy todas devuelven el ejemplo de datosEjemplo.js. Para conectar una sección con datos
// reales se cambia SOLO su función, por ejemplo:
//
//   export const getClima = (municipio) => obtener("/api/principal/clima", { municipio });
//
// La pantalla no cambia mientras la forma del objeto devuelto sea la misma.
import * as ejemplo from "./datosEjemplo.js";

// Simula una consulta al backend. Se borra cuando la sección deje de usar el ejemplo.
const simular = (datos) => Promise.resolve(datos);

export const getParcela = () => simular(ejemplo.parcela);

export const getAviso = (municipio) => simular(ejemplo.aviso);

// `esEjemplo` hace que la tarjeta muestre "DATOS DE EJEMPLO" en lugar de "DATOS REALES".
export const getClima = (municipio) =>
  simular({ pronostico: ejemplo.pronostico, hoy: ejemplo.hoy, esEjemplo: true });

export const getAlertaRegional = (municipio) => simular(ejemplo.alertaRegional);

export const getCultivoActivo = (municipio) => simular(ejemplo.cultivoActivo);

export const getPlanAnual = () => simular(ejemplo.planAnual);
