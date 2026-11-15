// Traduce los datos técnicos a frases simples para el agricultor. Cada color y frase sale de una
// clase OFICIAL (no se inventan umbrales):
// - Humedad del suelo vs. otros años: cortes por percentil del Drought Monitor (no es "sequía" oficial).
// - Plantas: clases de NDVI del USGS.
// - Terreno: clases de pendiente de la FAO.
// - Agua bajo tierra: signo de la tendencia de GRACE.
// - pH: clases del Soil Survey Manual del USDA (6.6-7.3 neutro).

export const COLORES = {
  bien: "var(--verde-oscuro)",
  ojo: "#d69a00",
  alerta: "#e8742c",
  mal: "var(--coral)",
  info: "var(--invierno)",
};

// Escala de sequía por percentil (Drought Monitor), de lo más seco a lo normal
export const TRAMOS_SEQUIA = [
  { hasta: 2, color: "#7a0a0a", etiqueta: "Mucho más seco de lo normal" },
  { hasta: 5, color: "#d7191c", etiqueta: "Mucho más seco de lo normal" },
  { hasta: 10, color: "#e8742c", etiqueta: "Más seco de lo normal" },
  { hasta: 20, color: "#f6c07a", etiqueta: "Más seco de lo normal" },
  { hasta: 30, color: "#f7e15a", etiqueta: "Un poco más seco de lo normal" },
  { hasta: 100, color: "#8fd9a8", etiqueta: "Normal o más húmedo" },
];

// Escala de pendiente (FAO, en %); se dibuja de 0 a 30 % para que se vean los tramos bajos
export const TRAMOS_PENDIENTE = [
  { hasta: 2, color: "#8fd9a8", etiqueta: "Plano o casi plano" },
  { hasta: 5, color: "#c6eb8f", etiqueta: "Ligeramente inclinado" },
  { hasta: 10, color: "#f7e15a", etiqueta: "Inclinado" },
  { hasta: 15, color: "#f6c07a", etiqueta: "Fuertemente inclinado" },
  { hasta: 30, color: "#e8742c", etiqueta: "Escarpado" },
];

// Escala de plantas (NDVI, USGS)
export const TRAMOS_NDVI = [
  { hasta: 0.1, color: "#c98b5a", etiqueta: "Suelo desnudo" },
  { hasta: 0.2, color: "#e9c27a", etiqueta: "Vegetación muy escasa" },
  { hasta: 0.3, color: "#e5e08a", etiqueta: "Matorral o pastizal" },
  { hasta: 0.6, color: "#9fdc8c", etiqueta: "Vegetación moderada" },
  { hasta: 1, color: "#3fa96b", etiqueta: "Vegetación densa" },
];

export function colorNdvi(v) {
  return TRAMOS_NDVI.find((t) => v <= t.hasta)?.color ?? TRAMOS_NDVI.at(-1).color;
}

export function resumenAgua(d) {
  if (!d || d.mensaje) return null;
  // percentil = % de años que estuvieron MÁS SECOS que hoy en estas mismas fechas
  const masSecos = Math.round(d.percentil / 10);
  const frase =
    d.percentil >= 40 && d.percentil <= 60
      ? "Hoy está como en un año típico para esta época"
      : d.percentil > 60
      ? `Hoy está más húmedo que ${masSecos} de cada 10 años en esta época`
      : `Hoy está más seco que ${10 - masSecos} de cada 10 años en esta época`;
  if (!d.categoria) return { tono: "bien", titulo: "Normal para esta época", frase };
  const tono = { D0: "ojo", D1: "alerta", D2: "alerta", D3: "mal", D4: "mal" }[d.categoria];
  const titulo = d.estado[0].toUpperCase() + d.estado.slice(1);
  return { tono, titulo, frase };
}

// El backend manda los meses abreviados (caben en la gráfica); en las frases van completos
const MES_COMPLETO = {
  ene: "enero", feb: "febrero", mar: "marzo", abr: "abril", may: "mayo", jun: "junio",
  jul: "julio", ago: "agosto", sep: "septiembre", oct: "octubre", nov: "noviembre", dic: "diciembre",
};
export const mesCompleto = (m) => MES_COMPLETO[m] ?? m;

export function resumenPlantas(d) {
  if (!d?.ultimo) return null;
  const c = d.ultimo.clase;
  const tono = c === "suelo desnudo" ? "mal" : c === "vegetación muy escasa" ? "alerta" : c === "matorral o pastizal" ? "ojo" : "bien";
  const titulo = { "suelo desnudo": "Terreno pelón", "vegetación muy escasa": "Muy pocas plantas", "matorral o pastizal": "Pocas plantas", "vegetación moderada": "Plantas regulares", "vegetación densa": "Muchas plantas" }[c];
  const menor = d.mes_menor_cobertura?.mes;
  const frase = d.meses_suelo_desnudo.length
    ? `Se queda sin plantas en ${d.meses_suelo_desnudo.map(mesCompleto).join(", ")}: ahí la tierra se puede perder`
    : menor
      ? `El mes con menos plantas es ${mesCompleto(menor)}`
      : "";
  return { tono, titulo, frase };
}

export function resumenTerreno(d) {
  if (!d?.clase_pendiente_fao) return null;
  const p = d.terreno.pendiente_promedio_pct;
  const tono = p <= 5 ? "bien" : p <= 10 ? "ojo" : p <= 15 ? "alerta" : "mal";
  const ls = d.factor_ls?.ls_promedio;
  const frase =
    ls == null
      ? ""
      : ls <= 1
        ? "La forma del terreno no aumenta la pérdida de tierra con la lluvia"
        : `La forma del terreno multiplica por ${ls} la pérdida de tierra con la lluvia`;
  const titulo = d.clase_pendiente_fao[0].toUpperCase() + d.clase_pendiente_fao.slice(1);
  return { tono, titulo, frase };
}

export function resumenAguaSubterranea(d) {
  if (!d) return null;
  const t = d.tendencia_cm_por_anio;
  if (t < 0) return { tono: "mal", titulo: "Bajando con los años", frase: "En tu región hay cada vez menos agua guardada (pozos, suelo, presas)" };
  if (t > 0) return { tono: "bien", titulo: "Subiendo con los años", frase: "En tu región hay cada vez más agua guardada" };
  return { tono: "info", titulo: "Sin cambio", frase: "El agua guardada en tu región se mantiene" };
}

export function resumenTipoSuelo(d) {
  const capa = d?.capas?.[0];
  if (!capa || capa.ph == null) return null;
  const ph = capa.ph < 6.6 ? "ácido" : capa.ph <= 7.3 ? "neutro" : "alcalino";
  const tex = capa.textura ?? "";
  return { tono: "info", titulo: `${tex[0]?.toUpperCase() ?? ""}${tex.slice(1)}`, frase: `Suelo ${ph} (pH ${capa.ph})` };
}
