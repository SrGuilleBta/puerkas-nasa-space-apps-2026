// Lluvia diaria (barras, eje derecho) y humedad medida por SMAP (puntos unidos, eje izquierdo).
// Sirve para ver cuánto sube la humedad con cada lluvia y qué tan rápido baja.
// `proximos` ([{fecha, mm}]) agrega la lluvia pronosticada a la derecha, y una barra con `estimada` (lluvia que POWER aún
// no trae) se dibuja más clara: son estimaciones, no mediciones.

export default function GraficaRetencion({ dias, proximos = [] }) {
  const W = 960, H = 260, M = { t: 14, r: 64, b: 28, l: 48 }; // ancho: va en una tarjeta de lado a lado
  const hum = dias.map((d) => d.humedad_pct_volumen).filter((v) => v != null);
  if (hum.length < 2) return <p className="suelo-nota">SMAP does not have enough recent measurements.</p>;

  const todos = [...dias, ...proximos.map((p) => ({ fecha: p.fecha, lluvia_mm: p.mm, estimada: true, pronostico: true }))];
  const lluvias = todos.map((d) => d.lluvia_mm ?? 0);
  const hMin = Math.floor(Math.min(...hum) - 2), hMax = Math.ceil(Math.max(...hum) + 2);
  const lMax = Math.max(10, Math.ceil(Math.max(...lluvias)));
  const ancho = (W - M.l - M.r) / todos.length;
  const x = (i) => M.l + ancho * (i + 0.5);
  const yH = (v) => M.t + (1 - (v - hMin) / (hMax - hMin)) * (H - M.t - M.b);
  const yL = (v) => H - M.b - (v / lMax) * (H - M.t - M.b);

  const puntos = dias.map((d, i) => (d.humedad_pct_volumen != null ? [x(i), yH(d.humedad_pct_volumen)] : null)).filter(Boolean);
  const linea = puntos.map((p, k) => `${k ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const iPronostico = dias.length;
  const etiquetas = [0, Math.floor(dias.length / 2), todos.length - 1];
  const fecha = (f) => `${f.slice(8, 10)}/${f.slice(5, 7)}`;

  return (
    <div className="suelo-grafica">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Daily rain, forecast rain and soil moisture">
        {[hMin, (hMin + hMax) / 2, hMax].map((v, k) => (
          <g key={k}>
            <line x1={M.l} x2={W - M.r} y1={yH(v)} y2={yH(v)} className="suelo-grafica-rejilla" />
            <text x={M.l - 6} y={yH(v) + 4} textAnchor="end" className="suelo-grafica-texto">{v.toFixed(0)}%</text>
          </g>
        ))}
        {[0, lMax].map((v, k) => (
          <text key={k} x={W - M.r + 6} y={yL(v) + 4} className="suelo-grafica-texto">{v} mm</text>
        ))}
        {proximos.length > 0 && (
          <g>
            <rect x={x(iPronostico) - ancho / 2} y={M.t} width={W - M.r - (x(iPronostico) - ancho / 2)} height={H - M.t - M.b} className="suelo-proy__zona" />
            <text x={x(iPronostico) - ancho / 2 + 6} y={M.t + 12} className="suelo-grafica-texto">Forecast</text>
            <text x={x(iPronostico) - ancho / 2 + 6} y={M.t + 28} className="suelo-grafica-texto">
              {Math.round(proximos.reduce((s, p) => s + (p.mm ?? 0), 0) * 10) / 10} mm
            </text>
          </g>
        )}
        {todos.map((d, i) =>
          d.lluvia_mm ? (
            <rect
              key={d.fecha}
              x={x(i) - ancho * 0.35}
              y={yL(d.lluvia_mm)}
              width={ancho * 0.7}
              height={H - M.b - yL(d.lluvia_mm)}
              fill="var(--verano)"
              fillOpacity={d.estimada ? 0.2 : 0.45}
              stroke={d.estimada ? "var(--verano)" : "none"}
              strokeDasharray={d.estimada ? "3 2" : undefined}
              rx="1.5"
            >
              <title>{`${fecha(d.fecha)}: ${d.lluvia_mm} mm${d.pronostico ? " (forecast)" : d.estimada ? " (estimate)" : ""}`}</title>
            </rect>
          ) : null
        )}
        <path d={linea} fill="none" stroke="var(--verde-oscuro)" strokeWidth="2" strokeLinejoin="round" />
        {puntos.map((p, k) => (
          <circle key={k} cx={p[0]} cy={p[1]} r="3" fill="var(--verde-oscuro)" />
        ))}
        {etiquetas.map((i, k) => (
          <text key={k} x={x(i)} y={H - 6} textAnchor={k === 0 ? "start" : k === 2 ? "end" : "middle"} className="suelo-grafica-texto">
            {fecha(todos[i].fecha)}
          </text>
        ))}
      </svg>
      <p className="suelo-leyenda">
        <span className="suelo-leyenda__linea" /> SMAP moisture (% vol.) <span className="suelo-leyenda__barra" /> Rain (mm/day)
        {todos.some((d) => d.estimada) && (
          <>
            {" "}
            <span className="suelo-leyenda__barra suelo-leyenda__barra--estimada" /> Estimated or forecast rain
          </>
        )}
      </p>
    </div>
  );
}
