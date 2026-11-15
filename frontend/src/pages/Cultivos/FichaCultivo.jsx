import { Alerta, Brote, Menos, Mas } from "../../components/Iconos.jsx";
import Tarjeta from "../../components/Tarjeta.jsx";
import { colorPorTexto } from "../../utils/colores.js";
import { NIVELES, miles, textoCiclo, textoMeses, textoRango } from "../../utils/cultivos.js";
import GuiaCultivo from "./GuiaCultivo.jsx";

function nombreZona(u) {
  if (u.nivel === "municipality") return `${u.nombre}, ${u.estado}`;
  return u.nombre;
}

// Si el cultivo no tiene descripción curada: la región que describe la agenda INIFAP, o una frase
// armada con lo que sí se sabe (tipo, familia, superficie sembrada).
function descripcion(d, zona) {
  const { ficha, indicadores: ind, nacional, manejo } = d;
  if (ficha.descripcion) return ficha.descripcion;
  const region = manejo.fichas?.find((f) => f.region)?.region;
  if (region) return region;
  const tipo = ficha.tipo && ficha.tipo !== "Other" ? ficha.tipo.toLowerCase() : null;
  const partes = [];
  if (tipo) partes.push(`${ficha.nombre} is a ${tipo} crop${ficha.familia ? ` of the ${ficha.familia} family` : ""}.`);
  if (nacional) partes.push(`${tipo ? "Across Mexico it" : `${ficha.nombre} is grown in Mexico and it`} is planted on about ${miles(nacional.superficie_sembrada_prom_ha)} ha, in ${miles(nacional.n_municipios)} municipalities.`);
  if (d.sembrado_en_ubicacion && ind && zona !== "Mexico") partes.push(`In ${zona} it covers about ${miles(ind.superficie_sembrada_prom_ha)} ha.`);
  return partes.join(" ");
}

function Dato({ etiqueta, valor, nota }) {
  return (
    <div className="enc__dato">
      <span>{etiqueta}</span>
      <strong>{valor ?? "—"}</strong>
      {nota && <small>{nota}</small>}
    </div>
  );
}

// Ficha de un cultivo en una zona: la pantalla central del Figma (cabecera, etiquetas,
// "situación actual" y "acerca de este cultivo") y, debajo, la guía de cultivo.
export default function FichaCultivo({ datos: d }) {
  const { ficha, indicadores: ind, manejo } = d;
  const zona = nombreZona(d.ubicacion);
  const color = colorPorTexto(ficha.id);
  const ciclo = textoCiclo(ficha.ciclo_dias, ficha.perenne);
  const agua = ficha.agua?.consumo;
  const meses = textoMeses(manejo.siembra_meses ?? []);
  const fichaInifap = manejo.fichas?.[0];
  const rend = ind?.rendimiento;
  const enZona = d.ubicacion.nivel !== "national";

  let notaSiembra = null;
  if (!meses) notaSiembra = enZona ? "No INIFAP data for this state" : "Pick a state";
  else if (fichaInifap) notaSiembra = `INIFAP · ${d.ubicacion.estado ?? d.ubicacion.nombre}`;

  const aviso =
    enZona && !d.sembrado_en_ubicacion
      ? `${ficha.nombre} is not grown in ${zona} according to SIAP. ${
          d.nivel_datos === "national" ? "Showing national data." : `Showing data for ${d.ubicacion_datos?.nombre ?? "the state"}.`
        }`
      : null;

  return (
    <div className="enc__ficha">
      {aviso && <p className="aviso aviso--info">{aviso}</p>}

      <Tarjeta className="enc__principal">
        <header className="enc__cabecera" style={{ "--color": color }}>
          <div className="enc__emblema" aria-hidden="true">
            <Brote size={56} />
          </div>
          <div className="enc__titulos">
            <p className="enc__tipo">{ficha.tipo ?? "Crop"}</p>
            <h1>{ficha.nombre}</h1>
            <p className="enc__cientifico">
              {ficha.cientifico && <em>{ficha.cientifico}</em>}
              {ficha.cientifico && ficha.nombre_es && " · "}
              {ficha.nombre_es && <span lang="es">{ficha.nombre_es}</span>}
            </p>
            <div className="enc__chips">
              {ciclo && <span className="enc__chip">Cycle {ciclo}</span>}
              {agua && <span className="enc__chip">Water: {NIVELES[agua] ?? agua}</span>}
              {ficha.eppocode && <span className="enc__chip enc__chip--suave">EPPO {ficha.eppocode}</span>}
            </div>
          </div>
        </header>

        {ind?.etiquetas?.length > 0 && (
          <ul className="enc__etiquetas">
            {ind.etiquetas.slice(0, 3).map((e) => (
              <li key={e.titulo} className={`enc__etiqueta enc__etiqueta--${e.tipo}`}>
                <span className="enc__signo" aria-hidden="true">
                  {e.tipo === "positive" ? <Mas size={14} /> : <Menos size={14} />}
                </span>
                <div>
                  <strong>{e.titulo}</strong>
                  <small>{e.detalle}</small>
                </div>
              </li>
            ))}
          </ul>
        )}

        <section className="enc__seccion" aria-labelledby="enc-situacion">
          <h2 id="enc-situacion">For your current situation</h2>
          {ind?.situacion_actual?.length > 0 ? (
            <ul className="enc__alertas">
              {ind.situacion_actual.map((a) => (
                <li key={a.titulo} className={`enc__alerta enc__alerta--${a.tipo}`}>
                  <Alerta size={22} />
                  <div>
                    <strong>{a.titulo}</strong>
                    <small>{a.detalle}</small>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="enc__nada">Nothing unusual for this crop in {zona} right now.</p>
          )}
        </section>

        <section className="enc__seccion" aria-labelledby="enc-acerca">
          <h2 id="enc-acerca">About this crop</h2>
          <p className="enc__texto">{descripcion(d, zona)}</p>
          {ficha.suelo && (
            <p className="enc__texto enc__texto--suave">
              <strong>Soil:</strong> {ficha.suelo}
            </p>
          )}

          <div className="enc__datos">
            <Dato etiqueta="Ideal planting" valor={meses} nota={notaSiembra} />
            <Dato etiqueta="Optimal temp." valor={textoRango(ficha.temperatura_optima_c, "°C")} nota={ficha.temperatura_optima_c ? "EcoCrop" : "No data for this crop"} />
            <Dato
              etiqueta="Yield"
              valor={rend?.p50 != null ? `${rend.p50} ${rend.unidad}` : null}
              nota={rend?.p25 != null && rend?.p75 != null ? `Typical ${rend.p25}–${rend.p75} · ${zona}` : zona}
            />
          </div>

          {ind && (
            <div className="enc__datos enc__datos--secundarios">
              <Dato
                etiqueta="Farm-gate price"
                valor={ind.precio?.pmr_real_ultimo != null ? `$${miles(ind.precio.pmr_real_ultimo)} ${ind.precio.unidad.replace("MXN", "").replace("/", "per ")}`.trim() : null}
                nota={ind.precio?.pmr_real_ultimo != null ? `${ind.anio_ultimo}, in ${ind.precio.anio_base} pesos` : null}
              />
              <Dato
                etiqueta="Water risk"
                valor={NIVELES[ind.riesgo_hidrico?.nivel]}
                nota={ind.riesgo_hidrico?.pct_riego != null ? `${Math.round(ind.riesgo_hidrico.pct_riego * 100)}% of the area is irrigated` : null}
              />
              <Dato
                etiqueta="Drought sensitivity"
                valor={NIVELES[ind.sensibilidad_sequia]}
                nota={ind.siniestro?.n_temporadas_sequia ? `${ind.siniestro.n_temporadas_sequia} severe-drought seasons studied` : null}
              />
              <Dato
                etiqueta="Flooding sensitivity"
                valor={NIVELES[d.sensibilidad_inundacion?.nivel]}
                nota={d.sensibilidad_inundacion?.nivel ? "From drainage tolerance (EcoCrop)" : "No data for this crop"}
              />
            </div>
          )}
        </section>
      </Tarjeta>

      <GuiaCultivo datos={d} zona={zona} />
    </div>
  );
}
