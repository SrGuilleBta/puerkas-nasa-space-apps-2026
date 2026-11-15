// Lluvia diaria (barras, eje derecho) y humedad medida por SMAP (puntos unidos, eje izquierdo).
// Sirve para ver cuánto sube la humedad con cada lluvia y qué tan rápido baja.

export default function GraficaRetencion({ dias }) {
  const W = 960, H = 260, M = { t: 14, r: 64, b: 28, l: 48 }; // ancho: va en una tarjeta de lado a lado
  const hum = dias.map((d) => d.humedad_pct_volumen).filter((v) => v != null);
  const lluvias = dias.map((d) => d.lluvia_mm ?? 0);
  if (hum.length < 2) return <p className="suelo-nota">SMAP no tiene suficientes mediciones recientes.</p>;

  const hMin = Math.floor(Math.min(...hum) - 2), hMax = Math.ceil(Math.max(...hum) + 2);
  const lMax = Math.max(10, Math.ceil(Math.max(...lluvias)));
  const ancho = (W - M.l - M.r) / dias.length;
  const x = (i) => M.l + ancho * (i + 0.5);
  const yH = (v) => M.t + (1 - (v - hMin) / (hMax - hMin)) * (H - M.t - M.b);
  const yL = (v) => H - M.b - (v / lMax) * (H - M.t - M.b);

  const puntos = dias.map((d, i) => (d.humedad_pct_volumen != null ? [x(i), yH(d.humedad_pct_volumen)] : null)).filter(Boolean);
  const linea = puntos.map((p, k) => `${k ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const etiquetas = [0, Math.floor(dias.length / 2), dias.length - 1];
  const fecha = (f) => `${f.slice(8, 10)}/${f.slice(5, 7)}`;

  return (
    <div className="suelo-grafica">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Lluvia diaria y humedad del suelo">
        {[hMin, (hMin + hMax) / 2, hMax].map((v, k) => (
          <g key={k}>
            <line x1={M.l} x2={W - M.r} y1={yH(v)} y2={yH(v)} className="suelo-grafica-rejilla" />
            <text x={M.l - 6} y={yH(v) + 4} textAnchor="end" className="suelo-grafica-texto">{v.toFixed(0)}%</text>
          </g>
        ))}
        {[0, lMax].map((v, k) => (
          <text key={k} x={W - M.r + 6} y={yL(v) + 4} className="suelo-grafica-texto">{v} mm</text>
        ))}
        {dias.map((d, i) =>
          d.lluvia_mm ? (
            <rect
              key={d.fecha}
              x={x(i) - ancho * 0.35}
              y={yL(d.lluvia_mm)}
              width={ancho * 0.7}
              height={H - M.b - yL(d.lluvia_mm)}
              fill="var(--verano)"
              fillOpacity="0.45"
              rx="1.5"
            />
          ) : null
        )}
        <path d={linea} fill="none" stroke="var(--verde-oscuro)" strokeWidth="2" strokeLinejoin="round" />
        {puntos.map((p, k) => (
          <circle key={k} cx={p[0]} cy={p[1]} r="3" fill="var(--verde-oscuro)" />
        ))}
        {etiquetas.map((i, k) => (
          <text key={k} x={x(i)} y={H - 6} textAnchor={k === 0 ? "start" : k === 2 ? "end" : "middle"} className="suelo-grafica-texto">
            {fecha(dias[i].fecha)}
          </text>
        ))}
      </svg>
      <p className="suelo-leyenda">
        <span className="suelo-leyenda__linea" /> Humedad SMAP (% vol.) <span className="suelo-leyenda__barra" /> Lluvia (mm/día)
      </p>
    </div>
  );
}
