// fetch común al backend. El frontend nunca llama a APIs externas: todo pasa por /api.

// Error de la API. `mensaje` es el texto para mostrarle al usuario y `datos` trae lo extra
// que mande el backend (por ejemplo `libreDesde` cuando una siembra se traslapa).
export class ErrorApi extends Error {
  constructor(mensaje, { estado = 0, datos = {} } = {}) {
    super(mensaje);
    this.name = "ErrorApi";
    this.estado = estado;
    this.datos = datos;
  }
}

// El backend responde {"detail": {"mensaje": "..."}} en los errores del Planificador,
// {"detail": "texto"} en los demás y {"detail": [ ... ]} cuando FastAPI valida los campos.
function leerError(estado, cuerpo, ruta) {
  const detalle = cuerpo?.detail;
  if (detalle && typeof detalle === "object" && !Array.isArray(detalle) && detalle.mensaje) {
    return new ErrorApi(detalle.mensaje, { estado, datos: detalle });
  }
  if (typeof detalle === "string") return new ErrorApi(detalle, { estado });
  if (Array.isArray(detalle)) return new ErrorApi("Revisa los datos: hay campos vacíos o inválidos.", { estado });
  return new ErrorApi(`No se pudo completar la solicitud a ${ruta} (${estado})`, { estado });
}

async function pedir(metodo, ruta, parametros, cuerpo) {
  const consulta = new URLSearchParams(parametros);
  const url = consulta.size ? `${ruta}?${consulta}` : ruta;
  const opciones = { method: metodo };
  if (cuerpo !== undefined) {
    opciones.headers = { "Content-Type": "application/json" };
    opciones.body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(url, opciones);
  } catch {
    throw new ErrorApi("No hay conexión con el servidor.");
  }

  if (!respuesta.ok) {
    const json = await respuesta.json().catch(() => null);
    throw leerError(respuesta.status, json, ruta);
  }
  return respuesta.status === 204 ? null : respuesta.json();
}

export const obtener = (ruta, parametros = {}) => pedir("GET", ruta, parametros);

// Para crear, editar o borrar: enviar("POST", ruta, cuerpo)
export const enviar = (metodo, ruta, cuerpo) => pedir(metodo, ruta, {}, cuerpo);
