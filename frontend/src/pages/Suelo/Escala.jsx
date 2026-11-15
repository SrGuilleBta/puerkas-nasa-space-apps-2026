// Barra de colores con una flecha "estás aquí". `tramos` = [{ hasta, color, etiqueta }] en orden;
// `valor` se ubica en la escala de `min` a `max`.

export default function Escala({ tramos, valor, min = 0, max = 100, extremos = [] }) {
  const pos = (v) => ((Math.min(Math.max(v, min), max) - min) / (max - min)) * 100;
  let inicio = min;
  return (
    <div className="escala">
      <div className="escala__barra">
        {tramos.map((t) => {
          const izq = pos(inicio);
          const ancho = pos(t.hasta) - izq;
          inicio = t.hasta;
          return (
            <span
              key={t.hasta} // la etiqueta puede repetirse entre tramos; el límite superior no
              className="escala__tramo"
              style={{ left: `${izq}%`, width: `${ancho}%`, background: t.color }}
              title={t.etiqueta}
            />
          );
        })}
        {valor != null && (
          <span className="escala__marca" style={{ left: `${pos(valor)}%` }} aria-label="Your land is here">
            ▼
          </span>
        )}
      </div>
      {extremos.length === 2 && (
        <div className="escala__extremos">
          <span>{extremos[0]}</span>
          <span>{extremos[1]}</span>
        </div>
      )}
    </div>
  );
}
