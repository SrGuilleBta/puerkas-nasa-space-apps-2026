import { useEffect } from "react";
import { getPlan, listarPlanes } from "../api/planificador.js";
import useDatos from "../hooks/useDatos.js";
import { numero } from "../utils/formato.js";
import { leerPlanActivo } from "../utils/planActivo.js";

// El plan que se está viendo: el elegido en el Planificador y, si ya no existe, el primero.
async function cargarPlanActivo() {
  const planes = await listarPlanes();
  const guardado = leerPlanActivo();
  const id = (planes.find((p) => p.id === guardado) ?? planes[0])?.id;
  return id ? getPlan(id) : null;
}

const plural = (n, palabra) => `${n} ${palabra}${n === 1 ? "" : "s"}`;

// Resumen del plan activo al pie del menú lateral. Se vuelve a pedir cada vez que se abre el menú,
// porque el plan o sus parcelas pudieron cambiar en el Planificador desde la última vez.
export default function PlanLateral({ abierto }) {
  const { datos: plan, cargando, error, recargar } = useDatos(cargarPlanActivo, []);

  useEffect(() => {
    if (abierto) recargar();
  }, [abierto, recargar]);

  let contenido;
  if (plan) {
    const hectareas = plan.parcelas.reduce((suma, p) => suma + p.hectareas, 0);
    contenido = (
      <>
        <strong>{plan.nombre}</strong>
        <span>
          {plural(plan.parcelas.length, "plot")} · {numero(hectareas)} ha
        </span>
      </>
    );
  } else if (cargando) {
    contenido = <span>Loading…</span>;
  } else {
    contenido = <span>{error ? "Plan unavailable" : "No plan yet"}</span>;
  }

  return (
    <div className="layout__plan">
      <p>Active plan</p>
      {contenido}
    </div>
  );
}
