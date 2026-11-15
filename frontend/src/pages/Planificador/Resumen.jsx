import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { deISO, fechaConAnio } from "../../utils/fechas.js";

const ha = (n) => Number(n.toFixed(1)); // 14.200000000000001 -> 14.2

function enDias(n) {
  if (n === 0) return "hoy";
  return n === 1 ? "mañana" : `en ${n} días`;
}

// Números del plan que se está viendo. Lo que depende del mercado (rentabilidad) todavía no está.
export default function Resumen({ resumen }) {
  const { proximaCosecha: proxima } = resumen;
  return (
    <Tarjeta>
      <EncabezadoTarjeta etiqueta="Resumen del ciclo" titulo="Tu plan de un vistazo" />

      <dl className="resumen">
        <div className="resumen__dato">
          <dt>Siembras</dt>
          <dd>{resumen.totalSiembras}</dd>
          <small>{resumen.enCurso === 1 ? "1 en curso hoy" : `${resumen.enCurso} en curso hoy`}</small>
        </div>

        <div className="resumen__dato">
          <dt>Cultivos distintos</dt>
          <dd>{resumen.cultivosDistintos}</dd>
          <small>en todo el plan</small>
        </div>

        <div className="resumen__dato">
          <dt>Uso del suelo hoy</dt>
          <dd>{resumen.usoSuelo}%</dd>
          <div className="progreso" role="progressbar" aria-label="Uso del suelo" aria-valuenow={resumen.usoSuelo} aria-valuemin={0} aria-valuemax={100}>
            <i style={{ width: `${resumen.usoSuelo}%` }} />
          </div>
          <small>
            {ha(resumen.hectareasEnUso)} de {ha(resumen.hectareasTotales)} ha con cultivo
          </small>
        </div>

        <div className="resumen__dato">
          <dt>Próxima cosecha</dt>
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
              <small>No hay cosechas por venir</small>
            </>
          )}
        </div>
      </dl>
    </Tarjeta>
  );
}
