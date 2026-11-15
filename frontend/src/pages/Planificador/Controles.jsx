import { Flecha, Mas, Menos } from "../../components/Iconos.jsx";
import { NIVELES_ZOOM } from "../../utils/ventana.js";

// Selector de plan y controles del calendario (moverse en el tiempo y zoom).
export default function Controles({
  planes,
  planId,
  onPlan,
  onNuevoPlan,
  onEditarPlan,
  meses,
  onMover,
  onZoom,
  onHoy,
}) {
  const i = NIVELES_ZOOM.indexOf(meses);
  return (
    <div className="controles">
      <div className="controles__plan">
        <label className="campo controles__selector">
          <span className="sr-only">Plan</span>
          <select value={planId ?? ""} onChange={(e) => onPlan(Number(e.target.value))}>
            {planes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="btn" onClick={onEditarPlan}>
          Editar plan
        </button>
        <button type="button" className="btn btn--primario" onClick={onNuevoPlan}>
          Nuevo plan
        </button>
      </div>

      <div className="controles__tiempo" role="group" aria-label="Periodo del calendario">
        <button type="button" className="controles__icono controles__icono--atras" aria-label="Periodo anterior" onClick={() => onMover(-1)}>
          <Flecha size={16} />
        </button>
        <button type="button" className="btn" onClick={onHoy}>
          Hoy
        </button>
        <button type="button" className="controles__icono" aria-label="Periodo siguiente" onClick={() => onMover(1)}>
          <Flecha size={16} />
        </button>
        <span className="controles__zoom">
          <button type="button" className="controles__icono" aria-label="Ver menos meses" disabled={i <= 0} onClick={() => onZoom(-1)}>
            <Mas size={16} />
          </button>
          <output>{meses} meses</output>
          <button type="button" className="controles__icono" aria-label="Ver más meses" disabled={i >= NIVELES_ZOOM.length - 1} onClick={() => onZoom(1)}>
            <Menos size={16} />
          </button>
        </span>
      </div>
    </div>
  );
}
