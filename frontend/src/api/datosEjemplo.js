// DATOS DE EJEMPLO tomados del prototipo de Figma. Todavía no vienen del backend.
// Cuando cada dato tenga su endpoint (ver docs/funcionalidades.md), se reemplaza aquí
// por una función de src/api/ y la pantalla no cambia.

export const parcela = { nombre: "La Esperanza", hectareas: 12.4 };

export const aviso = {
  titulo: "Atención preventiva",
  texto: "Se aproxima un frente de lluvia intensa para el próximo mes. Considera ajustar el riego.",
};

// Un valor por día, de lunes a domingo.
export const pronostico = [
  { tmax: 28, lluvia: 10, cielo: "sol" },
  { tmax: 29, lluvia: 5, cielo: "sol" },
  { tmax: 27, lluvia: 20, cielo: "nube" },
  { tmax: 25, lluvia: 45, cielo: "lluvia" },
  { tmax: 26, lluvia: 20, cielo: "nube" },
  { tmax: 30, lluvia: 6, cielo: "sol" },
  { tmax: 24, lluvia: 70, cielo: "lluvia" },
];

export const hoy = {
  temperatura: 30,
  sensacion: 31,
  cielo: "Soleado",
  icono: "sol",
  optimoParaCampo: true,
  humedad: 48,
  vientoKmh: 12,
  humedadSuelo: 62,
  phSuelo: 6.8,
};

export const alertaRegional = {
  hace: "35 min",
  titulo: "Se pronostica un fuerte huracán en la zona norte del país",
  detalle: "Protección Civil recomienda revisar cultivos e infraestructura de riego.",
};
