const DIAS = ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"];
const MESES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

export const etiquetaDia = (fecha) => DIAS[fecha.getDay()];

export const mesCorto = (mes) => MESES[mes].slice(0, 3);

export const fechaLarga = (fecha) => `${fecha.getDate()} de ${MESES[fecha.getMonth()]}`;

export const fechaCorta = (fecha) => `${fecha.getDate()} ${mesCorto(fecha.getMonth())}`;

export const mismoDia = (a, b) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

// Los 7 días de la semana (lunes a domingo) que contiene a `fecha`.
export function semanaDe(fecha) {
  const lunes = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  lunes.setDate(lunes.getDate() - ((lunes.getDay() + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(lunes);
    d.setDate(lunes.getDate() + i);
    return d;
  });
}

// Posición de una fecha dentro de su año, de 0 a 100.
export function porcentajeDelAnio(fecha) {
  const inicio = new Date(fecha.getFullYear(), 0, 1);
  const fin = new Date(fecha.getFullYear() + 1, 0, 1);
  return ((fecha - inicio) / (fin - inicio)) * 100;
}

// ---------- Fechas AAAA-MM-DD (las del backend y de <input type="date">) ----------
// Se construyen con año, mes y día locales: new Date("2026-05-10") las leería como UTC y en
// México mostraría el 9 de mayo.
export const deISO = (texto) => {
  const [a, m, d] = texto.split("-").map(Number);
  return new Date(a, m - 1, d);
};

export const aISO = (fecha) =>
  `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}-${String(fecha.getDate()).padStart(2, "0")}`;

export const sumarDias = (fecha, dias) => {
  const d = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  d.setDate(d.getDate() + dias);
  return d;
};

// Días entre dos fechas (b - a), sin que el cambio de horario afecte el resultado.
export const diasEntre = (a, b) =>
  Math.round((Date.UTC(b.getFullYear(), b.getMonth(), b.getDate()) - Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())) / 86400000);

export const fechaConAnio = (fecha) => `${fecha.getDate()} ${mesCorto(fecha.getMonth())} ${fecha.getFullYear()}`;

// Compara textos sin importar acentos, mayúsculas ni espacios de más ("Maíz" = "maiz").
export const normalizar = (texto) =>
  texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
