import { mesCorto } from "../../utils/fechas.js";

// Rango típico de humedad de raíz de los próximos meses (barras de mínimo a máximo de cada mes en los años de la serie) y su
// promedio (punto). Es lo que suele pasar en este lugar, no un pronóstico de este año.
// `tipico` viene de tipicoProximosMeses() en estimaciones.js.

export default function TipicoMeses({ tipico }) {
  const W = 480, H = 190, M = { t: 14, r: 14, b: 26, l: 44 };
  const { meses } = tipico;
  const min = Math.floor(Math.min(...meses.map((m) => m.min)) - 1);
  const max = Math.ceil(Math.max(...meses.map((m) => m.max)) + 1);
  const ancho = (W - M.l - M.r) / meses.length;
  const y = (v) => M.t + (1 - (v - min) / (max - min)) * (H - M.t - M.b);

  return (
    <div className="suelo-grafica">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Typical root-zone moisture for the coming months">
        {[min, (min + max) / 2, max].map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className="suelo-grafica-rejilla" />
            <text x={M.l - 6} y={y(v) + 4} textAnchor="end" className="suelo-grafica-texto">
              {Math.round(v)}%
            </text>
          </g>
        ))}
        {meses.map((m, i) => {
          const cx = M.l + ancho * (i + 0.5);
          return (
            <g key={m.mes}>
              <rect x={cx - ancho * 0.28} y={y(m.max)} width={ancho * 0.56} height={y(m.min) - y(m.max)} rx="6" className="suelo-tipico__rango">
                <title>{`${mesCorto(m.mes)}: usually between ${m.min}% and ${m.max}%`}</title>
              </rect>
              <circle cx={cx} cy={y(m.promedio)} r="5" className="suelo-tipico__promedio">
                <title>{`${mesCorto(m.mes)}: average ${m.promedio}%`}</title>
              </circle>
              <text x={cx} y={H - 6} textAnchor="middle" className="suelo-grafica-texto">
                {mesCorto(m.mes)}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="suelo-proy__leyenda">
        <span>
          <i className="suelo-tipico__muestra suelo-tipico__muestra--rango" /> Usual range ({tipico.anios} years)
        </span>
        <span>
          <i className="suelo-tipico__muestra suelo-tipico__muestra--promedio" /> Average
        </span>
      </p>
    </div>
  );
}
