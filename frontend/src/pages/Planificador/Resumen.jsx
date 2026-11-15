import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { deISO, fechaConAnio } from "../../utils/fechas.js";

const ha = (n) => Number(n.toFixed(1)); // 14.200000000000001 -> 14.2

function enDias(n) {
  if (n === 0) return "today";
  return n === 1 ? "tomorrow" : `in ${n} days`;
}

// Números del plan que se está viendo. Lo que depende del mercado (rentabilidad) todavía no está.
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
      </dl>
    </Tarjeta>
  );
}
