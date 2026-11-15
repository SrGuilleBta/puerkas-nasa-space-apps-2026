// Cada cultivo tiene siempre el mismo color, en el Planificador y en Principal.
const PALETA = [
  "var(--verano)",
  "var(--primavera)",
  "var(--otono)",
  "var(--ambar)",
  "var(--invierno)",
  "var(--violeta)",
];

export const colorCultivo = (cultivoId) => PALETA[cultivoId % PALETA.length];

// Para cultivos con id de texto (enciclopedia): el mismo cultivo siempre sale del mismo color.
export function colorPorTexto(texto) {
  let h = 0;
  for (const c of texto) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PALETA[h % PALETA.length];
}
