// NDVI promedio por mes (barras), cada barra pintada con el color de su clase del USGS.

import { TRAMOS_NDVI, colorNdvi } from "./resumen.js";

export default function GraficaMeses({ meses }) {
  const W = 480, H = 190, M = { t: 12, r: 12, b: 26, l: 36 };
  const max = Math.max(0.8, ...meses.map((m) => m.ndvi_promedio ?? 0));
  const ancho = (W - M.l - M.r) / meses.length;
  const y = (v) => M.t + (1 - v / max) * (H - M.t - M.b);

  return (
    <div className="suelo-grafica">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Plantas en el terreno por mes">
        {[0, 0.3, 0.6].map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className="suelo-grafica-rejilla" />
            <text x={M.l - 6} y={y(v) + 4} textAnchor="end" className="suelo-grafica-texto">{v}</text>
          </g>
        ))}
        {meses.map((m, i) =>
          m.ndvi_promedio != null ? (
            <rect
              key={m.mes}
              x={M.l + ancho * i + ancho * 0.15}
              y={y(m.ndvi_promedio)}
              width={ancho * 0.7}
              height={y(0) - y(m.ndvi_promedio)}
              rx="3"
              fill={colorNdvi(m.ndvi_promedio)}
            >
              <title>{`${m.mes}: ${m.clase} (NDVI ${m.ndvi_promedio})`}</title>
            </rect>
          ) : null
        )}
        {meses.map((m, i) => (
          <text key={m.mes} x={M.l + ancho * (i + 0.5)} y={H - 6} textAnchor="middle" className="suelo-grafica-texto">
            {m.mes}
          </text>
        ))}
      </svg>
      <p className="suelo-leyenda">
        {TRAMOS_NDVI.map((t) => (
          <span key={t.etiqueta} className="suelo-leyenda__item">
            <span className="suelo-leyenda__color" style={{ background: t.color }} /> {t.etiqueta}
          </span>
        ))}
      </p>
    </div>
  );
}
