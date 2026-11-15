import { Gota } from "../../components/Iconos.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { fechaCorta } from "../../utils/fechas.js";
import GraficaProyeccion from "./GraficaProyeccion.jsx";

const dia = (iso) => fechaCorta(new Date(`${iso}T12:00:00`));

function Dato({ etiqueta, valor, nota }) {
  return (
    <div className="suelo-dato">
      <span className="suelo-dato__etiqueta">{etiqueta}</span>
      <span className="suelo-dato__valor">{valor}</span>
      {nota && <span className="suelo-proy__nota">{nota}</span>}
    </div>
  );
}

const FRASE_TENDENCIA = {
  baja: "Your soil is drying out",
  sube: "Your soil is getting wetter",
  estable: "Your soil moisture will hold steady",
};

// Hacia dónde va el suelo esta semana: humedad de la raíz, lluvia y pérdida de agua, y temperatura del suelo.
// Todo lo que va después del último dato de NASA es una estimación y así se rotula.
export default function Proyeccion({ nombre, d }) {
  const r = d.resumen;
  const real = d.real.slice(-8);
  const puntos = (campo) => ({
    real: real.map((p) => ({ fecha: p.fecha, y: p[campo] })),
    estimado: d.proyeccion.map((p) => ({ fecha: p.fecha, y: p[campo] })),
  });
  const cambio = `${r.cambio_pts > 0 ? "+" : ""}${r.cambio_pts}`;

  return (
    <Tarjeta className="suelo-proy">
      <EncabezadoTarjeta etiqueta={`Estimate · next 7 days · ${nombre}`} titulo="Where your soil is heading" />

      <p className={`suelo-proy__titulo suelo-proy__titulo--${r.tendencia}`}>
        <Gota size={20} /> {FRASE_TENDENCIA[r.tendencia]}
        <small>
          {" "}
          · root-zone moisture {r.humedad_raiz_hoy}% today → {r.humedad_raiz_final}% on {dia(r.fecha_final)} ({cambio} points)
        </small>
      </p>

      {r.lluvia_fuerte && (
        <p className="suelo-aviso suelo-proy__aviso" role="status">
          Heavy rain forecast on {dia(r.lluvia_fuerte.fecha)} ({r.lluvia_fuerte.mm} mm, {d.supuestos.umbral_lluvia_fuerte_mm} mm or more
          in a day). Bare or sloping land can lose soil, so check the Land and erosion card below.
        </p>
      )}

      <div className="suelo-datos">
        <Dato
          etiqueta="Rain expected"
          valor={`${r.lluvia_total_mm} mm`}
          nota={r.dias_con_lluvia === 0 ? "no rainy days" : `${r.dias_con_lluvia} ${r.dias_con_lluvia === 1 ? "day" : "days"} with 1 mm or more`}
        />
        <Dato etiqueta="Water lost" valor={`${r.perdida_total_mm} mm`} nota="evaporation + plants" />
        <Dato
          etiqueta="Soil temperature"
          valor={r.temperatura_suelo_min == null ? "—" : `${r.temperatura_suelo_min}–${r.temperatura_suelo_max}°C`}
          nota="surface, range of the week"
        />
      </div>

      <h3 className="suelo-proy__subtitulo">Root-zone moisture (% of saturation) and rain</h3>
      <GraficaProyeccion
        {...puntos("humedad_raiz")}
        hoy={d.hoy}
        unidad="%"
        color="var(--turquesa)"
        etiqueta="Root-zone moisture, measured and estimated, with forecast rain"
        barras={d.proyeccion.map((p) => ({ fecha: p.fecha, mm: p.lluvia_mm }))}
      />

      <h3 className="suelo-proy__subtitulo">Soil surface temperature</h3>
      <GraficaProyeccion
        {...puntos("temperatura_suelo")}
        hoy={d.hoy}
        unidad="°"
        color="var(--coral)"
        alto={200}
        etiqueta="Soil surface temperature, measured and estimated"
      />

      <p className="suelo-nota">
        This is an estimate, not a measurement. NASA POWER reports with a 2–3 day delay (latest value: {dia(d.ultimo_dato_real)}), so we
        continue from there with a simple water balance: forecast rain minus the water the land loses, based on how much it was losing
        in the last days (about {d.supuestos.factor_evaporacion} of the reference evapotranspiration). It assumes a 1 m root zone and an
        average soil and ignores runoff, so use it to see the trend, not to time an exact irrigation. Rain forecasts get less reliable
        after a few days.
      </p>
      <p className="suelo-fuente">Source: {d.fuente} · method: FAO Irrigation and Drainage Paper 56</p>
    </Tarjeta>
  );
}
