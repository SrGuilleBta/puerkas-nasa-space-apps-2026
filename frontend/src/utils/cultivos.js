// Utilidades de la enciclopedia de Cultivos.

const MESES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// [3, 4, 5, 6] -> "March — June". Si hay varias ventanas ([1, 2, 3, 7, 8]) las separa con " · ".
// Una ventana que cruza el fin de año ([11, 12, 1]) se junta: "November — January".
export function textoMeses(meses) {
  const orden = [...new Set(meses)].filter((m) => m >= 1 && m <= 12).sort((a, b) => a - b);
  if (orden.length === 0) return null;
  if (orden.length === 12) return "All year";
  const tiene = new Set(orden);
  // Empieza una ventana en cada mes cuyo anterior (circular) no está
  const inicios = orden.filter((m) => !tiene.has(m === 1 ? 12 : m - 1));
  const ventanas = inicios.map((ini) => {
    let fin = ini;
    while (tiene.has(fin === 12 ? 1 : fin + 1)) fin = fin === 12 ? 1 : fin + 1;
    return ini === fin ? MESES[ini - 1] : `${MESES[ini - 1]} — ${MESES[fin - 1]}`;
  });
  return ventanas.join(" · ");
}

// [18, 33] -> "18° — 33°C"
export const textoRango = (rango, unidad = "") =>
  rango && rango.length === 2 ? `${rango[0]}° — ${rango[1]}${unidad}` : null;

// [120, 150] -> "120–150 days"
export function textoCiclo(ciclo, perenne) {
  if (ciclo && ciclo.length === 2) return ciclo[0] === ciclo[1] ? `${ciclo[0]} days` : `${ciclo[0]}–${ciclo[1]} days`;
  return perenne ? "Perennial" : null;
}

export const NIVELES = { low: "Low", medium: "Medium", high: "High", no_evidence: "Not enough data" };

export const miles = (n) => (n == null ? "—" : Math.round(n).toLocaleString("en-US"));

// Texto sin acentos y en minúsculas, para que "maiz" encuentre "Maíz".
export const normalizar = (t) =>
  (t ?? "").normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().trim();

// Lee y escribe JSON en localStorage sin romper si el navegador lo bloquea.
export function leerJSON(clave, defecto) {
  try {
    const crudo = localStorage.getItem(clave);
    return crudo === null ? defecto : JSON.parse(crudo);
  } catch {
    return defecto;
  }
}
export function guardarJSON(clave, valor) {
  try {
    localStorage.setItem(clave, JSON.stringify(valor));
  } catch {
    /* sin almacenamiento: no se recuerda la elección */
  }
}
