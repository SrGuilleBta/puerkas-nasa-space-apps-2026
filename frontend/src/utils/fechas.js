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
