import { useId, useState } from "react";
import { deISO, fechaCorta } from "../../utils/fechas.js";

// Gráfica de precios en SVG (sin librerías). Recibe `series`: [{ id, nombre, color, puntos: [{ fecha, real, proyeccion }] }].
// El eje horizontal es de tiempo real (los puntos pueden estar separados por una semana). Lo real va en línea
// continua, la proyección punteada, y una línea vertical marca el último dato real.
const W = 640;
const H = 260;
const M = { t: 14, r: 16, b: 30, l: 52 };

export default function GraficaPrecios({ series, ultimoReal }) {
  const id = useId().replace(/:/g, "");
  const [activa, setActiva] = useState(null); // fecha bajo el cursor

  const todas = series.flatMap((s) => s.puntos);
  if (todas.length === 0) return <p className="mercado__nota">No prices in this range.</p>;

  const tiempos = todas.map((p) => deISO(p.fecha).getTime());
  const t0 = Math.min(...tiempos);
  const t1 = Math.max(...tiempos);
  const valores = todas.flatMap((p) => [p.real, p.proyeccion]).filter((v) => v != null);
  let min = Math.min(...valores);
  let max = Math.max(...valores);
  const holgura = (max - min || 1) * 0.08;
  min = Math.max(0, min - holgura);
  max += holgura;

  const x = (fecha) => M.l + ((deISO(fecha).getTime() - t0) / Math.max(1, t1 - t0)) * (W - M.l - M.r);
  const y = (v) => M.t + (1 - (v - min) / (max - min)) * (H - M.t - M.b);

  const trazo = (puntos, clave) => {
    let d = "";
    let anterior = false;
    for (const p of puntos) {
      if (p[clave] == null) {
        anterior = false;
        continue;
      }
      d += `${anterior ? "L" : "M"}${x(p.fecha).toFixed(1)},${y(p[clave]).toFixed(1)} `;
      anterior = true;
    }
    return d;
  };

  const marcasY = [0, 1, 2, 3].map((i) => min + ((max - min) * i) / 3);
  const marcasX = [0, 0.25, 0.5, 0.75, 1].map((f) => new Date(t0 + (t1 - t0) * f));
  const iso = (fecha) => fecha.toISOString().slice(0, 10);
  const xUltimo = ultimoReal && deISO(ultimoReal).getTime() >= t0 && deISO(ultimoReal).getTime() <= t1 ? x(ultimoReal) : null;

  // Punto de cada serie más cercano a la fecha bajo el cursor
  const alMover = (e) => {
    const caja = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - caja.left) / caja.width) * W;
    const t = t0 + ((px - M.l) / (W - M.l - M.r)) * (t1 - t0);
    const cercano = tiempos.reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a), tiempos[0]);
    setActiva(iso(new Date(cercano)));
  };
  const enActiva = (s) => s.puntos.reduce((a, p) => (a == null || Math.abs(deISO(p.fecha) - deISO(activa)) < Math.abs(deISO(a.fecha) - deISO(activa)) ? p : a), null);

  return (
    <div className="grafica-precios">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Price chart" onMouseMove={alMover} onMouseLeave={() => setActiva(null)}>
        {marcasY.map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className="grafica-precios__rejilla" />
            <text x={M.l - 6} y={y(v) + 4} textAnchor="end" className="grafica-precios__texto">
              {v.toFixed(0)}
            </text>
          </g>
        ))}
        {marcasX.map((f) => (
          <text key={f.getTime()} x={M.l + ((f.getTime() - t0) / Math.max(1, t1 - t0)) * (W - M.l - M.r)} y={H - 8} textAnchor="middle" className="grafica-precios__texto">
            {fechaCorta(f)}
          </text>
        ))}
        {xUltimo != null && (
          <g>
            <line x1={xUltimo} x2={xUltimo} y1={M.t} y2={H - M.b} className="grafica-precios__corte" />
            <text x={xUltimo + 4} y={M.t + 10} className="grafica-precios__texto">
              Last real price
            </text>
          </g>
        )}
        {series.map((s) => (
          <g key={s.id}>
            <path d={trazo(s.puntos, "real")} fill="none" stroke={s.color} strokeWidth="2.2" strokeLinejoin="round" />
            <path d={trazo(s.puntos, "proyeccion")} fill="none" stroke={s.color} strokeWidth="2.2" strokeDasharray="5 4" strokeLinejoin="round" opacity="0.85" />
          </g>
        ))}
        {activa && (
          <g>
            <line x1={x(activa)} x2={x(activa)} y1={M.t} y2={H - M.b} className="grafica-precios__cursor" />
            {series.map((s) => {
              const p = enActiva(s);
              const v = p && (p.real ?? p.proyeccion);
              return p && v != null ? <circle key={s.id} cx={x(p.fecha)} cy={y(v)} r="3.5" fill={s.color} stroke="#fff" strokeWidth="1.5" /> : null;
            })}
          </g>
        )}
        <desc id={id}>Solid lines are real retail prices, dashed lines are the projection.</desc>
      </svg>
      {activa && (
        <p className="grafica-precios__valores" aria-live="polite">
          <b>{fechaCorta(deISO(activa))}</b>
          {series.map((s) => {
            const p = enActiva(s);
            const v = p && (p.real ?? p.proyeccion);
            return (
              <span key={s.id}>
                <i style={{ background: s.color }} />
                {s.nombre} {v != null ? `$${v.toFixed(2)}` : "—"}
                {p && p.real == null && p.proyeccion != null ? " (projected)" : ""}
              </span>
            );
          })}
        </p>
      )}
    </div>
  );
}
