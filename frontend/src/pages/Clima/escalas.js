// Colores y valores del mapa de Clima. Cada capa tiene su escala: lluvia (mm) y calor (temperatura máxima, °C).

export const CAPAS = {
  lluvia: {
    unidad: "mm",
    // Del azul claro al violeta: más lluvia, más intenso
    paradas: ["#bae6fd", "#38bdf8", "#2563eb", "#7c3aed", "#d946ef"],
    dominio: (dia) => [0, dia === "semana" ? 100 : 40],
  },
  calor: {
    unidad: "°C",
    // Del turquesa al rojo: más calor, más rojo
    paradas: ["#22d3ee", "#4ade80", "#fde047", "#fb923c", "#ef4444"],
    dominio: () => [8, 40],
  },
};

// Valor de un punto en la capa y el día elegidos. `dia` es un número (0 = hoy) o "semana":
// la lluvia de la semana se suma y el calor de la semana es el máximo.
export function valorDe(punto, capa, dia) {
  const serie = capa === "lluvia" ? punto.lluviaMm : punto.tmax;
  if (dia !== "semana") return serie[dia] ?? null;
  const validos = serie.filter((v) => v != null);
  if (validos.length === 0) return null;
  return capa === "lluvia" ? Math.round(validos.reduce((a, b) => a + b, 0) * 10) / 10 : Math.max(...validos);
}

const aRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

// Color de la escala para un valor (entre las paradas se mezcla)
export function colorDe(capa, dia, valor) {
  const { paradas, dominio } = CAPAS[capa];
  const [min, max] = dominio(dia);
  const t = Math.min(1, Math.max(0, (valor - min) / (max - min)));
  const pos = t * (paradas.length - 1);
  const i = Math.min(paradas.length - 2, Math.floor(pos));
  const a = aRgb(paradas[i]);
  const b = aRgb(paradas[i + 1]);
  const f = pos - i;
  return `rgb(${a.map((c, k) => Math.round(c + (b[k] - c) * f)).join(",")})`;
}

// Qué tan visible es la mancha: la lluvia casi nula no se pinta; el calor siempre
export function opacidadDe(capa, dia, valor) {
  if (capa === "calor") return 0.8;
  if (valor < 0.2) return 0;
  const [, max] = CAPAS.lluvia.dominio(dia);
  return Math.min(0.9, 0.3 + (valor / max) * 0.8);
}

export const textoValor = (capa, valor) =>
  valor == null ? "—" : capa === "lluvia" ? `${valor < 10 ? valor.toFixed(1) : Math.round(valor)} mm` : `${Math.round(valor)}°`;
