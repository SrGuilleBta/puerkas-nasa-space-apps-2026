// DATOS DE EJEMPLO tomados del prototipo de Figma. Todavía no vienen del backend.
// Cuando cada dato tenga su endpoint (ver docs/funcionalidades.md), se reemplaza aquí
// por una función de src/api/ y la pantalla no cambia.

export const parcela = { nombre: "La Esperanza", hectareas: 12.4 };

export const aviso = {
  titulo: "Preventive notice",
  texto: "A heavy rain front is approaching next month. Consider adjusting irrigation.",
};

// Un valor por día, empezando hoy.
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
  cielo: "Sunny",
  icono: "sol",
  optimoParaCampo: true,
  humedad: 48,
  vientoKmh: 12,
  humedadSuelo: 62,
  phSuelo: 6.8,
};

