// "What does this mean?": explica en palabras simples los términos técnicos de Suelo (el reto pide
// explicar evapotranspiración, anomalías de humedad, NDVI, etc. a agricultores sin experiencia técnica).
// Usa <details>, así funciona con teclado y lector de pantalla sin código extra.

export const GLOSARIO = {
  percentil: {
    titulo: "Percentile (moisture compared with other years)",
    texto:
      "It tells how many years were drier than today at this same time of year. A percentile of 80 means 8 out of 10 years were drier; a percentile of 10 means only 1 out of 10 was drier, so today is unusually dry. This difference from the usual is called a soil moisture anomaly.",
  },
  modelo: {
    titulo: "Model data (NASA POWER)",
    texto:
      "These numbers are not measured in your field: a NASA computer model estimates them from weather and satellite data, for squares of about 50 km. Surface is the top few centimeters, root zone is where most roots drink (down to about 1 m) and profile is the whole soil column. Moisture is shown as % of saturation: 100 % means the soil cannot hold more water.",
  },
  evaporacion: {
    titulo: "Evaporation and evapotranspiration",
    texto:
      "Evaporation is the water that leaves the soil as vapor, in millimeters per day (1 mm = 1 liter per square meter). Evapotranspiration adds the water that plants release through their leaves. If it is higher than the rain for many days, the soil dries out: that comparison is called the water balance.",
  },
  smap: {
    titulo: "Satellite measurement (SMAP)",
    texto:
      "The SMAP satellite measures the natural microwave signal of the ground, which changes with the water in the top 5 cm of soil. Each measurement covers a 9 km square, so it describes the area around your field, not one spot. Dense vegetation, cities and water make it less accurate. A probe in the ground measures one exact spot; the satellite covers everything, every 2–3 days. Using both gives the best picture.",
  },
  raiz: {
    titulo: "Root-zone moisture (SMAP L4)",
    texto:
      "The satellite only sees the top 5 cm. To estimate the water down to 1 m, where roots drink, NASA runs a model and corrects it every day with the SMAP measurements. It is an estimate, not a direct measurement.",
  },
  ndvi: {
    titulo: "NDVI (vegetation index)",
    texto:
      "It measures how green the land is, from the light that plants reflect: healthy leaves reflect a lot of near-infrared light and absorb red light. It goes from 0 to 1: 0.1 or less is bare soil, 0.2–0.3 is sparse grass or shrubs and 0.6 or more is dense vegetation. Months with bare soil are when rain and wind can carry the soil away.",
  },
  retencion: {
    titulo: "How the soil holds water",
    texto:
      "Each bar is a rain and the line is the soil moisture. If moisture goes up with the rain and stays up, water is soaking in (infiltration) and the soil keeps it. If it drops again in a day or two, the water runs off or drains fast. Organic matter and plant cover help the soil keep water.",
  },
  propiedades: {
    titulo: "pH, texture and organic matter",
    texto:
      "pH tells if the soil is acidic (below 6.6), neutral or alkaline (above 7.3); each crop grows best in a range. Texture is the mix of clay, sand and silt: clay holds water and nutrients but drains slowly, sand drains fast and holds little. Organic carbon comes from plant and animal remains; organic matter is about 1.7 times the carbon and improves structure, water holding and fertility. These values come from a world soil map (SoilGrids), not from a lab test of your field.",
  },
  erosion: {
    titulo: "Slope, LS factor and heavy rain",
    texto:
      "Slope is how steep the land is in %. The LS factor (from the RUSLE erosion equation) says how much the length and steepness of the slope increase soil loss: 1 is the standard test plot, 2 means twice the loss with the same rain and soil. Days with 20 mm or more of rain are the storms that wash soil away the most, especially on bare land.",
  },
  mapa: {
    titulo: "Soil map of Mexico (NASA POWER)",
    texto:
      "Each colored spot is a square of about 55 km where a NASA model estimates the soil moisture and temperature from satellite and weather data. It shows which regions are drier or wetter right now, not the exact value of your field. For your own place, the cards above use the nearest cropland point and the SMAP satellite.",
  },
  grace: {
    titulo: "Water stored in the region (GRACE)",
    texto:
      "The GRACE satellites measure tiny changes in Earth's gravity: when a region loses water (aquifers, soil, dams), it weighs less. The result is in centimeters of water compared with the 2004–2009 average, for areas of about 300 km. A falling line over many years means the region is using more water than it receives.",
  },
};

export default function Ayuda({ termino }) {
  const t = GLOSARIO[termino];
  if (!t) return null;
  return (
    <details className="ayuda">
      <summary>What does this mean?</summary>
      <p>
        <b>{t.titulo}.</b> {t.texto}
      </p>
    </details>
  );
}
