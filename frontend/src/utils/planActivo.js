// El plan que el usuario está viendo. Lo comparten el Planificador y Principal, así Principal
// muestra los cultivos y el calendario del mismo plan que se eligió en el Planificador.
const CLAVE = "planActivo";

export function leerPlanActivo() {
  try {
    const id = Number(localStorage.getItem(CLAVE));
    return Number.isInteger(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function guardarPlanActivo(id) {
  try {
    localStorage.setItem(CLAVE, String(id));
  } catch {
    /* sin almacenamiento: se usa el primer plan la próxima vez */
  }
}
