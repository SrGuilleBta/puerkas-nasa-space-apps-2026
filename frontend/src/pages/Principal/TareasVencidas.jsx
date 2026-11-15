import { Alerta, Flecha } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";

const atraso = (dias) => (dias === 1 ? "1 day late" : `${dias} days late`);

// Aviso de las tareas del Planificador que ya pasaron de fecha y siguen sin hacerse.
// No aparece si no hay ninguna. Muestra la más atrasada y cuántas más hay.
export default function TareasVencidas({ total, tareas }) {
  if (total === 0) return null;
  const peor = tareas[0];
  const mas = total - 1;
  return (
    <div className="banner banner--tareas" role="status">
      <span className="banner__icono">
        <Alerta size={18} />
      </span>
      <p className="banner__titulo">{total === 1 ? "1 overdue task" : `${total} overdue tasks`}</p>
      <p className="banner__texto">
        {peor.titulo} for {peor.cultivo} · {peor.parcela} ({atraso(peor.diasRetraso)})
        {mas > 0 ? ` and ${mas} more` : ""}.
      </p>
      <a className="banner__accion" href={hashDe("planificador")}>
        Open Planner <Flecha size={14} />
      </a>
    </div>
  );
}
