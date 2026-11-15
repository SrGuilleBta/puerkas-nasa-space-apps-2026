import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { deISO, fechaConAnio } from "../../utils/fechas.js";
import { pesos } from "../../utils/formato.js";

const ha = (n) => Number(n.toFixed(1)); // 14.200000000000001 -> 14.2

function enDias(n) {
  if (n === 0) return "today";
  return n === 1 ? "tomorrow" : `in ${n} days`;
}

// Números del plan que se está viendo. La economía solo cuenta las siembras en las que la persona capturó
// rendimiento, precio o costo; si no hay ninguna, esa tarjeta no aparece.
function Economia({ resumen }) {
  if (!resumen.siembrasConEconomia) return null;
  const { gananciaEstimada: ganancia, ingresoEstimado: ingreso, inversionEstimada: inversion } = resumen;
  const titulo = ganancia != null ? "Estimated profit" : ingreso != null ? "Estimated income" : "Estimated investment";
  const valor = ganancia ?? ingreso ?? inversion;
  const partes = [ingreso != null && `Income ${pesos(ingreso)}`, inversion != null && `Cost ${pesos(inversion)}`].filter(Boolean);
  return (
    <div className="resumen__dato">
      <dt>{titulo}</dt>
      <dd className={`resumen__texto ${valor < 0 ? "economia__perdida" : ""}`}>{pesos(valor)}</dd>
      <small>
        {partes.join(" · ")}
        {partes.length ? " · " : ""}
        {resumen.siembrasConEconomia} {resumen.siembrasConEconomia === 1 ? "planting" : "plantings"} with data
      </small>
    </div>
  );
}

function Tareas({ resumen }) {
  if (!resumen.tareasPendientes) return null;
  return (
    <div className="resumen__dato">
      <dt>Open tasks</dt>
      <dd>{resumen.tareasPendientes}</dd>
      <small className={resumen.tareasVencidas ? "economia__perdida" : ""}>
        {resumen.tareasVencidas ? `${resumen.tareasVencidas} overdue` : "None overdue"}
      </small>
    </div>
  );
}

export default function Resumen({ resumen }) {
  const { proximaCosecha: proxima } = resumen;
  return (
    <Tarjeta>
      <EncabezadoTarjeta etiqueta="Cycle summary" titulo="Your plan at a glance" />

      <dl className="resumen">
        <div className="resumen__dato">
          <dt>Plantings</dt>
          <dd>{resumen.totalSiembras}</dd>
          <small>{`${resumen.enCurso} in progress today`}</small>
        </div>

        <div className="resumen__dato">
          <dt>Distinct crops</dt>
          <dd>{resumen.cultivosDistintos}</dd>
          <small>across the whole plan</small>
        </div>

        <div className="resumen__dato">
          <dt>Land use today</dt>
          <dd>{resumen.usoSuelo}%</dd>
          <div className="progreso" role="progressbar" aria-label="Land use" aria-valuenow={resumen.usoSuelo} aria-valuemin={0} aria-valuemax={100}>
            <i style={{ width: `${resumen.usoSuelo}%` }} />
          </div>
          <small>
            {ha(resumen.hectareasEnUso)} of {ha(resumen.hectareasTotales)} ha under crops
          </small>
        </div>

        <div className="resumen__dato">
          <dt>Next harvest</dt>
          {proxima ? (
            <>
              <dd className="resumen__texto">{proxima.cultivo}</dd>
              <small>
                {proxima.parcela} · {fechaConAnio(deISO(proxima.fecha))} ({enDias(proxima.diasRestantes)})
              </small>
            </>
          ) : (
            <>
              <dd className="resumen__texto">—</dd>
              <small>No upcoming harvests</small>
            </>
          )}
        </div>

        <Economia resumen={resumen} />
        <Tareas resumen={resumen} />
      </dl>
    </Tarjeta>
  );
}
