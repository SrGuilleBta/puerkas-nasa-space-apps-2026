// Gráfica de línea sencilla en SVG (sin librerías). Recibe puntos {x: etiqueta, y: número}.
// Con `colorPorSigno`, el área arriba de 0 se pinta verde y la de abajo roja (p. ej. GRACE).
// `extension` ({x, y}[]) sigue la línea con un trazo punteado a partir del último punto: es una estimación, no un dato.

import { useId } from "react";

export default function GraficaLinea({
  puntos,
  extension = [],
  unidad = "",
  color = "var(--verde-oscuro)",
  lineaCero = false,
  alto = 200,
  colorPorSigno = false,
}) {
  const id = useId().replace(/:/g, "");
  const validos = puntos.filter((p) => p.y !== null && p.y !== undefined);
  if (validos.length < 2) return <p className="suelo-nota">Not enough data to chart.</p>;

  const todos = [...puntos, ...extension];
  const W = 480, H = alto, M = { t: 12, r: 16, b: 28, l: 50 };
  const ys = [...validos, ...extension].map((p) => p.y);
  let min = Math.min(...ys), max = Math.max(...ys);
  if (lineaCero) { min = Math.min(min, 0); max = Math.max(max, 0); }
  if (min === max) { min -= 1; max += 1; }
  const x = (i) => M.l + (i / (todos.length - 1)) * (W - M.l - M.r);
  const y = (v) => M.t + (1 - (v - min) / (max - min)) * (H - M.t - M.b);
  const base = y(lineaCero ? 0 : min);

  let d = "";
  puntos.forEach((p, i) => {
    if (p.y === null || p.y === undefined) return;
    d += `${d === "" || puntos[i - 1]?.y == null ? "M" : "L"}${x(i).toFixed(1)},${y(p.y).toFixed(1)} `;
  });
  const iPrimero = puntos.indexOf(validos[0]);
  const ultimo = validos[validos.length - 1];
  const iUltimo = puntos.lastIndexOf(ultimo);
  const area = `${d} L${x(iUltimo).toFixed(1)},${base.toFixed(1)} L${x(iPrimero).toFixed(1)},${base.toFixed(1)} Z`;
  const trazoExtension =
    extension.length > 0
      ? `M${x(iUltimo).toFixed(1)},${y(ultimo.y).toFixed(1)} ` +
        extension.map((p, k) => `L${x(puntos.length + k).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ")
      : null;

  const marcas = [min, (min + max) / 2, max];
  const etiquetasX = [0, Math.floor((todos.length - 1) / 2), todos.length - 1];

  return (
    <div className="suelo-grafica">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Trend chart">
        {marcas.map((m, k) => (
          <g key={k}>
            <line x1={M.l} x2={W - M.r} y1={y(m)} y2={y(m)} className="suelo-grafica-rejilla" />
            <text x={M.l - 6} y={y(m) + 4} textAnchor="end" className="suelo-grafica-texto">
              {m.toFixed(1)}
            </text>
          </g>
        ))}
        {lineaCero && <line x1={M.l} x2={W - M.r} y1={y(0)} y2={y(0)} className="suelo-grafica-cero" />}
        {etiquetasX.map((i, k) => (
          <text key={k} x={x(i)} y={H - 6} textAnchor={k === 0 ? "start" : k === 2 ? "end" : "middle"} className="suelo-grafica-texto">
            {todos[i].x}
          </text>
        ))}
        {colorPorSigno ? (
          <>
            <defs>
              <clipPath id={`arriba${id}`}>
                <rect x="0" y="0" width={W} height={y(0)} />
              </clipPath>
              <clipPath id={`abajo${id}`}>
                <rect x="0" y={y(0)} width={W} height={H} />
              </clipPath>
            </defs>
            <path d={area} fill="var(--verde)" fillOpacity="0.35" clipPath={`url(#arriba${id})`} />
            <path d={area} fill="var(--coral)" fillOpacity="0.35" clipPath={`url(#abajo${id})`} />
          </>
        ) : (
          <path d={area} fill={color} fillOpacity="0.12" stroke="none" />
        )}
        <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        {trazoExtension && (
          <path d={trazoExtension} fill="none" stroke={color} strokeWidth="2.5" strokeDasharray="6 5" strokeLinejoin="round" />
        )}
        <circle cx={x(iUltimo)} cy={y(ultimo.y)} r="4" fill={color} />
      </svg>
      <p className="suelo-nota">Latest: {ultimo.y} {unidad} ({ultimo.x})</p>
    </div>
  );
}
