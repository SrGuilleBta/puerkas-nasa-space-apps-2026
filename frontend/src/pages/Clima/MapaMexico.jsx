import { useId, useState } from "react";
import { colorDe, opacidadDe, textoValor, valorDe } from "./escalas.js";

// Mapa de México en SVG (sin librerías): el contorno del país y, encima, una mancha de color por cada punto de la
// malla (lluvia o calor, según la capa). Las manchas se difuminan para que se vea una superficie continua y se
// recortan al contorno. Los lugares guardados salen con su valor. Al pasar el cursor se lee el punto más cercano.
const ANCHO = 1000;
const MARGEN = 30;
const ETIQUETA_ALTO = 38;

const hemisferio = (n, pos, neg) => `${Math.abs(n).toFixed(1)}°${n >= 0 ? pos : neg}`;

export default function MapaMexico({ datos, capa, dia }) {
  const id = useId().replace(/:/g, "");
  const [lectura, setLectura] = useState(null);
  const { caja, contorno, puntos, lugares, paso } = datos;

  // Longitud y latitud a coordenadas del dibujo. Se achica la longitud con el coseno de la latitud media
  // (~23.6° N) para que México no se vea ensanchado.
  const escalaX = Math.cos(((caja.latMin + caja.latMax) / 2) * (Math.PI / 180));
  const unidad = (ANCHO - 2 * MARGEN) / ((caja.lonMax - caja.lonMin) * escalaX);
  const alto = Math.round((caja.latMax - caja.latMin) * unidad + 2 * MARGEN);
  const px = (lon) => MARGEN + (lon - caja.lonMin) * escalaX * unidad;
  const py = (lat) => MARGEN + (caja.latMax - lat) * unidad;

  const manchas = puntos
    .map((p) => ({ ...p, valor: valorDe(p, capa, dia) }))
    .filter((p) => p.valor != null);
  const trazo = contorno.map(([lon, lat], i) => `${i ? "L" : "M"}${px(lon).toFixed(1)},${py(lat).toFixed(1)}`).join("") + "Z";
  const radio = paso * escalaX * unidad * 0.95;

  // Etiquetas de los lugares: a la derecha del punto (a la izquierda si no cabe) y, si chocan con otra, movidas
  // hacia arriba o abajo hasta encontrar un hueco.
  const etiquetas = [];
  for (const l of lugares) {
    const x = px(l.lon);
    const y = py(l.lat);
    const ancho = Math.max(76, l.nombre.split(",")[0].length * 8 + 16);
    const cajaX = x + 8 + ancho > ANCHO - 6 ? x - 8 - ancho : x + 8;
    const choca = (cajaY) =>
      etiquetas.some((o) => Math.abs(o.cajaX - cajaX) < Math.max(o.ancho, ancho) && Math.abs(o.cajaY - cajaY) < ETIQUETA_ALTO + 4);
    const cajaY = [-34, 8, -78, 52, -122].map((dy) => Math.min(alto - ETIQUETA_ALTO - 4, Math.max(4, y + dy))).find((c) => !choca(c)) ?? y - 34;
    etiquetas.push({ nombre: l.nombre, valor: valorDe(l, capa, dia), x, y, cajaX, cajaY, ancho });
  }

  // Punto de la malla más cercano al cursor (si está a menos de ~1.5 pasos)
  function alMover(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * ANCHO;
    const y = ((e.clientY - r.top) / r.height) * alto;
    let mejor = null;
    let distancia = Infinity;
    for (const p of manchas) {
      const d = Math.hypot(px(p.lon) - x, py(p.lat) - y);
      if (d < distancia) {
        distancia = d;
        mejor = p;
      }
    }
    setLectura(mejor && distancia < radio * 1.5 ? mejor : null);
  }

  return (
    <div className="clima-mapa">
      <svg
        viewBox={`0 0 ${ANCHO} ${alto}`}
        role="img"
        aria-label={`Map of Mexico showing ${capa === "lluvia" ? "forecast rain" : "forecast maximum temperature"}`}
        onPointerMove={alMover}
        onPointerLeave={() => setLectura(null)}
      >
        <defs>
          <pattern id={`${id}-cuadro`} width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M50 0H0V50" fill="none" stroke="rgba(120, 190, 220, 0.07)" />
          </pattern>
          <clipPath id={`${id}-pais`}>
            <path d={trazo} />
          </clipPath>
          <filter id={`${id}-difuso`} x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation={radio * 0.32} />
          </filter>
        </defs>

        <rect width={ANCHO} height={alto} fill={`url(#${id}-cuadro)`} />
        <path d={trazo} fill="rgba(20, 200, 192, 0.16)" />
        <g clipPath={`url(#${id}-pais)`}>
          <g filter={`url(#${id}-difuso)`}>
            {manchas.map((p) => {
              const o = opacidadDe(capa, dia, p.valor);
              return o > 0 && <circle key={`${p.lat},${p.lon}`} cx={px(p.lon)} cy={py(p.lat)} r={radio} fill={colorDe(capa, dia, p.valor)} fillOpacity={o} />;
            })}
          </g>
        </g>
        <path d={trazo} fill="none" stroke="rgba(94, 234, 212, 0.55)" strokeWidth="1.5" strokeLinejoin="round" />

        {etiquetas.map((e) => (
          <g key={e.nombre} className="clima-mapa__lugar">
            <circle cx={e.x} cy={e.y} r="4.5" fill="#fff" stroke="#0b1f3a" strokeWidth="2" />
            {e.y !== e.cajaY + ETIQUETA_ALTO - 4 && (
              <line x1={e.x} y1={e.y} x2={e.cajaX + (e.cajaX > e.x ? 0 : e.ancho)} y2={e.cajaY + ETIQUETA_ALTO / 2} stroke="rgba(255,255,255,0.4)" />
            )}
            <rect x={e.cajaX} y={e.cajaY} width={e.ancho} height={ETIQUETA_ALTO} rx="8" fill="rgba(11, 31, 58, 0.88)" stroke="rgba(255,255,255,0.15)" />
            <text x={e.cajaX + 8} y={e.cajaY + 15} className="clima-mapa__nombre">
              {e.nombre.split(",")[0]}
            </text>
            <text x={e.cajaX + 8} y={e.cajaY + 31} className="clima-mapa__valor">
              {textoValor(capa, e.valor)}
            </text>
          </g>
        ))}

        {lectura && <circle cx={px(lectura.lon)} cy={py(lectura.lat)} r="7" fill="none" stroke="#fff" strokeWidth="2" />}
      </svg>
      <p className="clima-mapa__lectura" aria-live="polite">
        {lectura
          ? `Near ${hemisferio(lectura.lat, "N", "S")}, ${hemisferio(lectura.lon, "E", "W")} · ${textoValor(capa, lectura.valor)}`
          : "Move over the map to read a value"}
      </p>
    </div>
  );
}
