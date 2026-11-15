import { useId, useMemo, useState } from "react";

import { getMapa } from "../../api/suelo.js";
import Cargable from "../../components/Cargable.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";
import Ayuda from "./Ayuda.jsx";

// Mapa de México con la humedad y la temperatura del suelo de NASA POWER (malla de 0.5°), dibujado igual que el mapa
// de Clima (pages/Clima/MapaMexico.jsx): SVG sin librerías, manchas difuminadas recortadas al contorno del país y los
// lugares guardados con su valor. Datos: GET /api/suelo/mapa (services/suelo/mapa.py).

const CAPAS = {
  humedad_raiz: {
    nombre: "Root zone",
    unidad: "%",
    // Del café (seco) al azul (saturado)
    paradas: ["#a16207", "#f59e0b", "#fde68a", "#86efac", "#22c55e", "#0ea5e9", "#1d4ed8"],
    dominio: [0, 100],
    nota: "Water in the top meter of soil, where most roots drink, as % of saturation (100 % = the soil cannot hold more).",
  },
  humedad_superficie: {
    nombre: "Topsoil",
    unidad: "%",
    paradas: ["#a16207", "#f59e0b", "#fde68a", "#86efac", "#22c55e", "#0ea5e9", "#1d4ed8"],
    dominio: [0, 100],
    nota: "Water in the top 5 cm of soil, as % of saturation. It changes fast with each rain.",
  },
  temperatura: {
    nombre: "Soil temperature",
    unidad: "°C",
    paradas: ["#38bdf8", "#4ade80", "#fde047", "#fb923c", "#ef4444"],
    dominio: [0, 35],
    nota: "Temperature of the land surface. Seeds of most crops need a warm enough soil to germinate.",
  },
};

const ANCHO = 1000;
const MARGEN = 30;
const ETIQUETA_ALTO = 38;

const aRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

function colorDe(capa, valor) {
  const { paradas, dominio } = CAPAS[capa];
  const t = Math.min(1, Math.max(0, (valor - dominio[0]) / (dominio[1] - dominio[0])));
  const pos = t * (paradas.length - 1);
  const i = Math.min(paradas.length - 2, Math.floor(pos));
  const a = aRgb(paradas[i]);
  const b = aRgb(paradas[i + 1]);
  const f = pos - i;
  return `rgb(${a.map((c, k) => Math.round(c + (b[k] - c) * f)).join(",")})`;
}

const textoValor = (capa, v) => (v == null ? "—" : `${Math.round(v)}${CAPAS[capa].unidad === "%" ? " %" : "°"}`);
const hemisferio = (n, pos, neg) => `${Math.abs(n).toFixed(1)}°${n >= 0 ? pos : neg}`;

function Dibujo({ datos, capa }) {
  const id = useId().replace(/:/g, "");
  const [lectura, setLectura] = useState(null);
  const { caja, contorno, puntos, lugares, paso } = datos;

  const escalaX = Math.cos(((caja.latMin + caja.latMax) / 2) * (Math.PI / 180));
  const unidad = (ANCHO - 2 * MARGEN) / ((caja.lonMax - caja.lonMin) * escalaX);
  const alto = Math.round((caja.latMax - caja.latMin) * unidad + 2 * MARGEN);
  const px = (lon) => MARGEN + (lon - caja.lonMin) * escalaX * unidad;
  const py = (lat) => MARGEN + (caja.latMax - lat) * unidad;

  const manchas = puntos.filter((p) => p[capa] != null);
  const trazo = contorno.map(([lon, lat], i) => `${i ? "L" : "M"}${px(lon).toFixed(1)},${py(lat).toFixed(1)}`).join("") + "Z";
  const radio = paso * escalaX * unidad * 0.95;

  const etiquetas = [];
  for (const l of lugares) {
    const x = px(l.lon);
    const y = py(l.lat);
    const ancho = Math.max(76, l.nombre.split(",")[0].length * 8 + 16);
    const cajaX = x + 8 + ancho > ANCHO - 6 ? x - 8 - ancho : x + 8;
    const choca = (cajaY) =>
      etiquetas.some((o) => Math.abs(o.cajaX - cajaX) < Math.max(o.ancho, ancho) && Math.abs(o.cajaY - cajaY) < ETIQUETA_ALTO + 4);
    const cajaY = [-34, 8, -78, 52, -122].map((dy) => Math.min(alto - ETIQUETA_ALTO - 4, Math.max(4, y + dy))).find((c) => !choca(c)) ?? y - 34;
    etiquetas.push({ nombre: l.nombre, valor: l[capa], x, y, cajaX, cajaY, ancho });
  }

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
    <div className="suelo-mapa">
      <svg
        viewBox={`0 0 ${ANCHO} ${alto}`}
        role="img"
        aria-label={`Map of Mexico showing ${CAPAS[capa].nombre.toLowerCase()} from NASA POWER`}
        onPointerMove={alMover}
        onPointerLeave={() => setLectura(null)}
      >
        <defs>
          <clipPath id={`${id}-pais`}>
            <path d={trazo} />
          </clipPath>
          <filter id={`${id}-difuso`} x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation={radio * 0.45} />
          </filter>
        </defs>
        <path d={trazo} fill="rgba(255, 255, 255, 0.06)" />
        <g clipPath={`url(#${id}-pais)`}>
          <g filter={`url(#${id}-difuso)`}>
            {manchas.map((p) => (
              <circle key={`${p.lat},${p.lon}`} cx={px(p.lon)} cy={py(p.lat)} r={radio} fill={colorDe(capa, p[capa])} fillOpacity={0.85} />
            ))}
          </g>
        </g>
        <path d={trazo} fill="none" stroke="rgba(255, 255, 255, 0.55)" strokeWidth="1.5" strokeLinejoin="round" />

        {etiquetas.map((e) => (
          <g key={e.nombre}>
            <circle cx={e.x} cy={e.y} r="4.5" fill="#fff" stroke="#0b1f3a" strokeWidth="2" />
            {e.y !== e.cajaY + ETIQUETA_ALTO - 4 && (
              <line x1={e.x} y1={e.y} x2={e.cajaX + (e.cajaX > e.x ? 0 : e.ancho)} y2={e.cajaY + ETIQUETA_ALTO / 2} stroke="rgba(255,255,255,0.4)" />
            )}
            <rect x={e.cajaX} y={e.cajaY} width={e.ancho} height={ETIQUETA_ALTO} rx="8" fill="rgba(11, 31, 58, 0.88)" stroke="rgba(255,255,255,0.15)" />
            <text x={e.cajaX + 8} y={e.cajaY + 15} className="suelo-mapa__nombre">
              {e.nombre.split(",")[0]}
            </text>
            <text x={e.cajaX + 8} y={e.cajaY + 31} className="suelo-mapa__valor">
              {textoValor(capa, e.valor)}
            </text>
          </g>
        ))}

        {lectura && <circle cx={px(lectura.lon)} cy={py(lectura.lat)} r="7" fill="none" stroke="#fff" strokeWidth="2" />}
      </svg>
      <p className="suelo-mapa__lectura" aria-live="polite">
        {lectura
          ? `Near ${hemisferio(lectura.lat, "N", "S")}, ${hemisferio(lectura.lon, "E", "W")} · ${textoValor(capa, lectura[capa])}`
          : "Move over the map to read a value"}
      </p>
    </div>
  );
}

function Leyenda({ capa }) {
  const { paradas, dominio, unidad } = CAPAS[capa];
  return (
    <div className="suelo-mapa__leyenda" aria-hidden="true">
      <span>
        {dominio[0]} {unidad}
        {unidad === "%" ? " (dry)" : ""}
      </span>
      <i style={{ background: `linear-gradient(90deg, ${paradas.join(", ")})` }} />
      <span>
        {dominio[1]}
        {unidad === "%" ? " % (saturated)" : "+ °C"}
      </span>
    </div>
  );
}

function Contenido({ datos, municipio }) {
  const [capa, setCapa] = useState("humedad_raiz");
  const lugares = useMemo(
    () => datos.lugares.slice().sort((a, b) => Number(b.nombre === municipio) - Number(a.nombre === municipio)),
    [datos, municipio],
  );
  return (
    <Tarjeta>
      <EncabezadoTarjeta
        etiqueta="NASA POWER · all of Mexico"
        titulo="Soil map of Mexico"
        derecha={
          <div className="suelo-mapa__capas" role="tablist" aria-label="Map layer">
            {Object.entries(CAPAS).map(([clave, c]) => (
              <button key={clave} type="button" role="tab" aria-selected={capa === clave} onClick={() => setCapa(clave)}>
                {c.nombre}
              </button>
            ))}
          </div>
        }
      />
      <Ayuda termino="mapa" />
      {datos.desactualizado && (
        <p className="suelo-aviso">NASA POWER did not answer, so this map shows the last data we had.</p>
      )}
      <Dibujo datos={datos} capa={capa} />
      <Leyenda capa={capa} />
      <p className="suelo-nota">
        {CAPAS[capa].nota} Average of the last {datos.dias_promedio} days with data, up to {datos.hasta}.
      </p>
      {lugares.length > 0 && (
        <ul className="suelo-mapa__lugares">
          {lugares.map((l) => (
            <li key={l.nombre} className={l.nombre === municipio ? "suelo-mapa__lugar--activo" : ""}>
              <span>{l.nombre}</span>
              <b>{textoValor(capa, l[capa])}</b>
            </li>
          ))}
        </ul>
      )}
      <p className="suelo-fuente">
        Source: {datos.fuente}, NASA model on a grid of {datos.puntos.length} points about 55 km apart. It shows the
        regional pattern, not your exact field.
      </p>
    </Tarjeta>
  );
}

export default function MapaSuelo({ municipio }) {
  const mapa = useDatos(getMapa, []);
  return (
    <Cargable estado={mapa} alto={420}>
      {(datos) => <Contenido datos={datos} municipio={municipio} />}
    </Cargable>
  );
}
