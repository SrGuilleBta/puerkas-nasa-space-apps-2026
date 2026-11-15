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
