import { getFicha } from "../../api/planificador.js";
import { getClimaNasa } from "../../api/principal.js";
import Cargable from "../../components/Cargable.jsx";
import useDatos from "../../hooks/useDatos.js";
import { aISO, deISO, diasEntre, fechaConAnio, sumarDias } from "../../utils/fechas.js";
import { etiquetaTipo } from "../../utils/tipos.js";

const dias = (n) => `${n} ${n === 1 ? "day" : "days"}`;

// Clima observado por satélite (NASA POWER) en tu zona: desde la siembra, o los últimos 30 días si aún no empieza.
function ClimaNasa({ municipio, inicio, fin, hoy }) {
  const empezo = hoy >= inicio;
  const desde = empezo ? (diasEntre(inicio, hoy) > 365 ? sumarDias(hoy, -365) : inicio) : sumarDias(hoy, -30);
  const hasta = empezo && fin < hoy ? fin : hoy;
  const datos = useDatos(() => getClimaNasa(municipio, desde, hasta), [municipio, aISO(desde), aISO(hasta)]);
  const titulo = !empezo ? "Last 30 days in your area" : fin < hoy ? "Weather during the cycle" : "Weather since planting";

  return (
    <section className="info-siembra__nasa" aria-label={titulo}>
      <h3>{titulo}</h3>
      <Cargable estado={datos} alto={64}>
        {(d) =>
          d.dias === 0 ? (
            <small>No NASA data for these dates yet (it is published with about a 2-day delay).</small>
          ) : (
            <>
              <dl className="info-siembra__nasa-datos">
                <div>
                  <dt>Rainfall</dt>
                  <dd>
                    {d.lluviaMm} mm <small>({dias(d.diasConLluvia)})</small>
                  </dd>
                </div>
                <div>
                  <dt>Average temperature</dt>
                  <dd>{d.tempMedia} °C</dd>
                </div>
                <div>
                  <dt>Min. / max.</dt>
                  <dd>
                    {d.tempMin} / {d.tempMax} °C
                  </dd>
                </div>
                <div>
                  <dt>Root-zone moisture</dt>
                  <dd>{d.humedadRaizPct}%</dd>
                </div>
                <div>
                  <dt>Solar radiation</dt>
                  <dd>
                    {d.radiacion} <small>MJ/m² per day</small>
                  </dd>
                </div>
              </dl>
              <small>
                NASA POWER satellite data · {dias(d.dias)} with data · {fechaConAnio(deISO(d.desde))} to {fechaConAnio(deISO(d.hasta))}
              </small>
            </>
          )
        }
      </Cargable>
    </section>
  );
}

const AGUA = { bajo: "Low", medio: "Medium", alto: "High" };
const rango = (r, unidad) => (r ? `${r[0]}–${r[1]}${unidad}` : "—");

// Ficha del cultivo (catálogo de Cultivos): condiciones ideales y cuidados. No aparece si el cultivo no viene del catálogo.
function FichaCultivo({ cultivoId }) {
  const ficha = useDatos(() => getFicha(cultivoId), [cultivoId]).datos;
  if (!ficha) return null;
  return (
    <section className="info-siembra__ficha" aria-label="Crop guide">
      <h3>Crop guide</h3>
      {ficha.descripcion && <p>{ficha.descripcion}</p>}
      <dl className="info-siembra__nasa-datos">
        <div>
          <dt>Best temperature</dt>
          <dd>{rango(ficha.temperaturaOptimaC, " °C")}</dd>
        </div>
        <div>
          <dt>Water use</dt>
          <dd>{AGUA[ficha.consumoAgua] ?? "—"}</dd>
        </div>
        <div>
          <dt>Best soil pH</dt>
          <dd>{rango(ficha.phOptimo, "")}</dd>
        </div>
        <div>
          <dt>Fixes nitrogen</dt>
          <dd>{ficha.fijaNitrogeno ? "Yes" : "No"}</dd>
        </div>
      </dl>
      {ficha.suelo && (
        <p>
          <b>Soil:</b> {ficha.suelo}
        </p>
      )}
      {ficha.cuidados.length > 0 && (
        <>
          <b>Care tips</b>
          <ul>
            {ficha.cuidados.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </>
      )}
      <small>
        Source: {ficha.fuentes.join(", ") || "Crops catalog"}.
        {!ficha.textoRevisado && " General draft text: confirm with a local technician before acting on it."}
      </small>
    </section>
  );
}

// Pestaña informativa de una siembra: estado, avance del ciclo y contexto dentro de su parcela.
export default function InfoSiembra({ parcela, siembra, hoy, municipio }) {
  const inicio = deISO(siembra.fechaSiembra);
  const fin = deISO(siembra.fechaCosecha);
  const total = Math.max(1, diasEntre(inicio, fin));
  const transcurridos = diasEntre(inicio, hoy);

  let estado, detalle, avance;
  if (hoy < inicio) {
    const faltan = diasEntre(hoy, inicio);
    estado = "Scheduled";
    detalle = `Planting in ${dias(faltan)}`;
    avance = 0;
  } else if (hoy > fin) {
    estado = "Harvested";
    detalle = `Ended ${dias(diasEntre(fin, hoy))} ago`;
    avance = 100;
  } else {
    const faltan = diasEntre(hoy, fin);
    estado = "In progress";
    detalle = `Day ${transcurridos + 1} of ${total + 1} · ${dias(faltan)} left until harvest`;
    avance = Math.round((transcurridos / total) * 100);
  }

  // Siembras vecinas en la misma parcela (ya vienen en el plan, sin consultar nada más)
  const ordenadas = [...parcela.siembras].sort((a, b) => a.fechaSiembra.localeCompare(b.fechaSiembra));
  const i = ordenadas.findIndex((s) => s.id === siembra.id);
  const anterior = ordenadas[i - 1];
  const siguiente = ordenadas[i + 1];
  const ocupa = Math.round((siembra.hectareas / parcela.hectareas) * 100);

  return (
    <div className="info-siembra">
      <div className="info-siembra__estado">
        <span className={`info-siembra__sello info-siembra__sello--${estado === "In progress" ? "curso" : "otro"}`}>{estado}</span>
        <p>{detalle}</p>
      </div>

      <div className="info-siembra__avance" role="progressbar" aria-valuenow={avance} aria-valuemin={0} aria-valuemax={100} aria-label="Cycle progress">
        <span style={{ width: `${avance}%` }} />
      </div>
      <p className="campo__ayuda">Cycle progress: {avance}%</p>

      <dl className="info-siembra__datos">
        <div>
          <dt>Crop</dt>
          <dd>
            {siembra.cultivo.nombre}
            <small>
              {etiquetaTipo(siembra.cultivo.tipo)} · {dias(siembra.cultivo.cicloDias)} cycle
            </small>
          </dd>
        </div>
        <div>
          <dt>Plot</dt>
          <dd>
            {parcela.nombre}
            <small>
              {siembra.hectareas} of {parcela.hectareas} ha ({ocupa}%)
            </small>
          </dd>
        </div>
        <div>
          <dt>Planting</dt>
          <dd>{fechaConAnio(inicio)}</dd>
        </div>
        <div>
          <dt>Harvest</dt>
          <dd>
            {fechaConAnio(fin)}
            <small>{dias(total)} long</small>
          </dd>
        </div>
      </dl>

      <FichaCultivo cultivoId={siembra.cultivo.id} />

      {municipio && <ClimaNasa municipio={municipio} inicio={inicio} fin={fin} hoy={hoy} />}

      <div className="info-siembra__vecinas">
        <p>
          <b>Before:</b> {anterior ? `${anterior.cultivo.nombre} (${etiquetaTipo(anterior.cultivo.tipo)})` : "nothing recorded"}
        </p>
        <p>
          <b>After:</b> {siguiente ? `${siguiente.cultivo.nombre} (${etiquetaTipo(siguiente.cultivo.tipo)})` : "nothing scheduled yet"}
        </p>
      </div>
    </div>
  );
}
