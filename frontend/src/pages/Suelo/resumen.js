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

// Escala de humedad por percentil (Drought Monitor), de lo más seco a lo normal
export const TRAMOS_SEQUIA = [
  { hasta: 2, color: "#7a0a0a", etiqueta: "Much drier than normal" },
  { hasta: 5, color: "#d7191c", etiqueta: "Much drier than normal" },
  { hasta: 10, color: "#e8742c", etiqueta: "Drier than normal" },
  { hasta: 20, color: "#f6c07a", etiqueta: "Drier than normal" },
  { hasta: 30, color: "#f7e15a", etiqueta: "Slightly drier than normal" },
  { hasta: 100, color: "#8fd9a8", etiqueta: "Normal or wetter" },
];

// Escala de pendiente (FAO, en %); se dibuja de 0 a 30 % para que se vean los tramos bajos
export const TRAMOS_PENDIENTE = [
  { hasta: 2, color: "#8fd9a8", etiqueta: "Flat or nearly level" },
  { hasta: 5, color: "#c6eb8f", etiqueta: "Gently sloping" },
  { hasta: 10, color: "#f7e15a", etiqueta: "Sloping" },
  { hasta: 15, color: "#f6c07a", etiqueta: "Strongly sloping" },
  { hasta: 30, color: "#e8742c", etiqueta: "Steep" },
];

// Escala de plantas (NDVI, USGS)
export const TRAMOS_NDVI = [
  { hasta: 0.1, color: "#c98b5a", etiqueta: "Bare soil" },
  { hasta: 0.2, color: "#e9c27a", etiqueta: "Very sparse vegetation" },
  { hasta: 0.3, color: "#e5e08a", etiqueta: "Shrubland or grassland" },
  { hasta: 0.6, color: "#9fdc8c", etiqueta: "Moderate vegetation" },
  { hasta: 1, color: "#3fa96b", etiqueta: "Dense vegetation" },
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
      ? "Today it is like a typical year for this season"
      : d.percentil > 60
      ? `Today it is wetter than ${masSecos} out of 10 years at this time of year`
      : `Today it is drier than ${10 - masSecos} out of 10 years at this time of year`;
  if (!d.categoria) return { tono: "bien", titulo: "Normal for this season", frase };
  const tono = { D0: "ojo", D1: "alerta", D2: "alerta", D3: "mal", D4: "mal" }[d.categoria];
  const titulo = d.estado[0].toUpperCase() + d.estado.slice(1);
  return { tono, titulo, frase };
}

// El backend manda los meses abreviados (caben en la gráfica); en las frases van completos
const MES_COMPLETO = {
  Jan: "January", Feb: "February", Mar: "March", Apr: "April", May: "May", Jun: "June",
  Jul: "July", Aug: "August", Sep: "September", Oct: "October", Nov: "November", Dec: "December",
};
export const mesCompleto = (m) => MES_COMPLETO[m] ?? m;

export function resumenPlantas(d) {
  if (!d?.ultimo) return null;
  const c = d.ultimo.clase;
  const tono = c === "bare soil" ? "mal" : c === "very sparse vegetation" ? "alerta" : c === "shrubland or grassland" ? "ojo" : "bien";
  const titulo = {
    "bare soil": "Bare land",
    "very sparse vegetation": "Very few plants",
    "shrubland or grassland": "Few plants",
    "moderate vegetation": "Some plants",
    "dense vegetation": "Many plants",
  }[c];
  const menor = d.mes_menor_cobertura?.mes;
  const frase = d.meses_suelo_desnudo.length
    ? `It is left without plants in ${d.meses_suelo_desnudo.map(mesCompleto).join(", ")}: the soil can be lost then`
    : menor
      ? `The month with the fewest plants is ${mesCompleto(menor)}`
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
        ? "The shape of the land does not increase soil loss from rain"
        : `The shape of the land multiplies soil loss from rain by ${ls}`;
  const titulo = d.clase_pendiente_fao[0].toUpperCase() + d.clase_pendiente_fao.slice(1);
  return { tono, titulo, frase };
}

export function resumenAguaSubterranea(d) {
  if (!d) return null;
  const t = d.tendencia_cm_por_anio;
  if (t < 0) return { tono: "mal", titulo: "Going down over the years", frase: "Your region stores less and less water (wells, soil, dams)" };
  if (t > 0) return { tono: "bien", titulo: "Going up over the years", frase: "Your region stores more and more water" };
  return { tono: "info", titulo: "No change", frase: "The water stored in your region stays the same" };
}

export function resumenTipoSuelo(d) {
  const capa = d?.capas?.[0];
  if (!capa || capa.ph == null) return null;
  const ph = capa.ph < 6.6 ? "Acidic" : capa.ph <= 7.3 ? "Neutral" : "Alkaline";
  const tex = capa.textura ?? "";
  return { tono: "info", titulo: `${tex[0]?.toUpperCase() ?? ""}${tex.slice(1)}`, frase: `${ph} soil (pH ${capa.ph})` };
}
