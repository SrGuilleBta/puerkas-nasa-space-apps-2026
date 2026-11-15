import { useId } from "react";
import { fechaCorta } from "../../utils/fechas.js";

// Línea de lo medido (continua) que sigue con la estimación (punteada), una marca en "hoy" y, si se pide, la lluvia
// pronosticada en barras. Es SVG sin librerías, como las otras gráficas de Suelo.
// `real` y `estimado` son [{fecha: "AAAA-MM-DD", y: número|null}]; `barras` es [{fecha, mm}].

const W = 960;
const M = { t: 14, r: 56, b: 28, l: 52 };
const dia = (iso) => fechaCorta(new Date(`${iso}T12:00:00`));

export default function GraficaProyeccion({ real, estimado, hoy, unidad, color, alto = 240, barras, etiqueta }) {
  const id = useId().replace(/:/g, "");
  const H = alto;
  const fechas = [...real.map((p) => p.fecha), ...estimado.map((p) => p.fecha)];
  const valores = [...real, ...estimado].map((p) => p.y).filter((v) => v != null);
  if (fechas.length < 2 || valores.length < 2) return <p className="suelo-nota">Not enough data to chart.</p>;

  const margen = Math.max(1, (Math.max(...valores) - Math.min(...valores)) * 0.15);
  const min = Math.floor(Math.min(...valores) - margen);
  const max = Math.ceil(Math.max(...valores) + margen);
  const paso = (W - M.l - M.r) / (fechas.length - 1);
  const x = (i) => M.l + i * paso;
  const y = (v) => M.t + (1 - (v - min) / (max - min)) * (H - M.t - M.b);
  const iHoy = fechas.indexOf(hoy);

  const trazo = (puntos, desde) =>
    puntos
      .map((p, k) => (p.y == null ? null : `${k === 0 ? "M" : "L"}${x(desde + k).toFixed(1)},${y(p.y).toFixed(1)}`))
      .filter(Boolean)
      .join(" ");
  const ultimoReal = real[real.length - 1];
  // La estimación arranca en el último dato real, para que la línea no tenga un hueco
  const trazoEstimado = trazo([ultimoReal, ...estimado], real.length - 1);
  const trazoReal = trazo(real, 0);

  const maxLluvia = barras ? Math.max(10, ...barras.map((b) => b.mm ?? 0)) : 0;
  const yLluvia = (mm) => H - M.b - (mm / maxLluvia) * (H - M.t - M.b) * 0.45; // las barras ocupan la parte baja
  const etiquetasX = [...new Set([0, iHoy >= 0 ? iHoy : null, fechas.length - 1].filter((i) => i != null))];

  return (
    <div className="suelo-grafica">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={etiqueta}>
        <defs>
          <linearGradient id={`${id}-fondo`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={color} stopOpacity="0.16" />
            <stop offset="1" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>

        {[min, (min + max) / 2, max].map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className="suelo-grafica-rejilla" />
            <text x={M.l - 6} y={y(v) + 4} textAnchor="end" className="suelo-grafica-texto">
              {Math.round(v * 10) / 10}
              {unidad}
            </text>
          </g>
        ))}

        {/* Zona estimada: de hoy hacia la derecha (lo de antes de hoy ya pasó, aunque POWER aún no lo trae) */}
        {iHoy >= 0 && (
          <rect x={x(iHoy)} y={M.t} width={W - M.r - x(iHoy)} height={H - M.t - M.b} fill={`url(#${id}-fondo)`} />
        )}

        {barras &&
          barras.map((b) => {
            const i = fechas.indexOf(b.fecha);
            if (i < 0 || !b.mm) return null;
            return (
              <rect
                key={b.fecha}
                x={x(i) - paso * 0.3}
                width={paso * 0.6}
                y={yLluvia(b.mm)}
                height={H - M.b - yLluvia(b.mm)}
                rx="3"
                className="suelo-proy__lluvia"
              >
                <title>{`${dia(b.fecha)}: ${b.mm} mm rain forecast`}</title>
              </rect>
            );
          })}

        {iHoy >= 0 && (
          <g>
            <line x1={x(iHoy)} x2={x(iHoy)} y1={M.t} y2={H - M.b} className="suelo-grafica-cero" />
            <text x={x(iHoy) + 6} y={M.t + 12} className="suelo-grafica-texto">
              Today
            </text>
          </g>
        )}

        <path d={trazoReal} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
        <path d={trazoEstimado} fill="none" stroke={color} strokeWidth="2.5" strokeDasharray="7 6" strokeLinejoin="round" />
        {[...real, ...estimado].map((p, i) =>
          p.y == null ? null : (
            <circle key={fechas[i]} cx={x(i)} cy={y(p.y)} r="3.5" fill={i < real.length ? color : "#fff"} stroke={color} strokeWidth="2">
              <title>{`${dia(fechas[i])}: ${p.y}${unidad}${i < real.length ? "" : " (estimate)"}`}</title>
            </circle>
          ),
        )}

        {etiquetasX.map((i, k) => (
          <text
            key={i}
            x={x(i)}
            y={H - 6}
            textAnchor={k === 0 ? "start" : i === fechas.length - 1 ? "end" : "middle"}
            className="suelo-grafica-texto"
          >
            {dia(fechas[i])}
          </text>
        ))}
      </svg>
      <p className="suelo-proy__leyenda">
        <span>
          <i className="suelo-proy__trazo" style={{ borderColor: color }} /> Measured by NASA
        </span>
        <span>
          <i className="suelo-proy__trazo suelo-proy__trazo--punteado" style={{ borderColor: color }} /> Estimate
        </span>
        {barras && (
          <span>
            <i className="suelo-proy__barra" /> Forecast rain (mm)
          </span>
        )}
      </p>
    </div>
  );
}
