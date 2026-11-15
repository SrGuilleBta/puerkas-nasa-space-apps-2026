// Los tipos de cultivo se guardan en español en la base y en la API (las reglas del backend dependen
// de esos valores). La interfaz es en inglés, así que siempre se muestran con estas etiquetas.
export const TIPOS = ["cereal", "leguminosa", "frutal", "hortaliza", "oleaginosa", "forraje", "otro"];

const ETIQUETAS = {
  cereal: "Cereal",
  leguminosa: "Legume",
  frutal: "Fruit",
  hortaliza: "Vegetable",
  oleaginosa: "Oilseed",
  forraje: "Forage",
  otro: "Other",
};

export const etiquetaTipo = (tipo) => ETIQUETAS[tipo] ?? tipo;
