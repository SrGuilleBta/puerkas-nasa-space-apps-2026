import { useEffect, useState } from "react";
import { getPlagas } from "../../api/planificador.js";
import { fechaConAnio, deISO } from "../../utils/fechas.js";

const NIVEL = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };
const TIPO = { insect: "Insect or mite", fungus: "Fungus or mold", pathogen: "Bacterium or virus" };
const ESPERA_MS = 3000;
const INTENTOS = 60; // unos 3 minutos: la primera consulta de un cultivo tarda

const km = (n) => `${Math.round(n)} km`;

function Presencia({ p }) {
  if (!p.detectada) return <>No records within {p.radioKm} km (this only means nobody has reported it nearby).</>;
  return (
    <>
      {p.registros} {p.registros === 1 ? "record" : "records"} within {p.radioKm} km; the nearest is {km(p.masCercanoKm)} away
      {p.lugar ? ` (${p.lugar})` : ""}
      {p.ultimoRegistro ? `, ${p.ultimoRegistro}` : ""}.
    </>
  );
}

function Plaga({ p }) {
  const lista = (titulo, items) =>
    items.length > 0 && (
      <p>
        <b>{titulo}:</b> {items.join(", ")}
      </p>
    );
  return (
    <details className="plaga">
      <summary>
        <span className={`plaga__punto plaga__punto--${p.riesgo}`} aria-hidden="true" />
        <span className="plaga__nombre">
          {p.nombre}
          <small>
            {TIPO[p.tipo] ?? p.tipo} · <i>{p.nombreCientifico}</i>
          </small>
        </span>
        <span className={`plaga__nivel plaga__nivel--${p.riesgo}`}>{NIVEL[p.riesgo]}</span>
      </summary>
      <div className="plaga__detalle">
        <p>
          <b>{p.diagnostico}.</b> {p.accion}
        </p>
        <p>
          <b>Nearby records:</b> <Presencia p={p.presencia} />
        </p>
        <p>
          <b>Weather:</b>{" "}
          {p.tipo === "fungus"
            ? `${p.rachaDias} favorable ${p.rachaDias === 1 ? "day" : "days"} in a row`
            : `${p.gradosDia} degree-days in the window`}
          {p.diasFavorables.length > 0 && ` · ${p.diasFavorables.length} favorable ${p.diasFavorables.length === 1 ? "day" : "days"}`}.
        </p>
        {lista("Host crops (avoid rotating with them)", p.hospederos)}
        {lista("Spread by", p.vectores)}
        {lista("Biological control", p.controlBiologico)}
        {lista("Quarantine status", p.cuarentena)}
        <small>Status in Mexico: {p.estadoPais}</small>
      </div>
    </details>
  );
}

// Una línea para la cabecera cerrada: "4 critical · 8 high" (o lo que haya).
function textoResumen(r) {
  const partes = ["critical", "high", "medium", "low"].filter((n) => r.conteo[n] > 0).map((n) => `${r.conteo[n]} ${n}`);
  return partes.length > 0 ? partes.join(" · ") : "nothing to check";
}

// Plagas y enfermedades de un cultivo del catálogo y su riesgo hoy en la ubicación activa (motor de plagas:
// EPPO + clima + registros de GBIF e iNaturalist). La primera vez de un cultivo tarda: se vuelve a preguntar
// cada pocos segundos hasta que el análisis esté listo.
export default function PlagasCultivo({ catalogoId, municipio }) {
  const [estado, setEstado] = useState({ cargando: true });

  useEffect(() => {
    let vigente = true;
    let temporizador;
    setEstado({ cargando: true });

    const preguntar = (intento) => {
      getPlagas(catalogoId, municipio)
        .then((r) => {
          if (!vigente) return;
          if (r.estado === "calculando" && intento < INTENTOS) {
            setEstado({ calculando: true });
            temporizador = setTimeout(() => preguntar(intento + 1), ESPERA_MS);
          } else if (r.estado === "calculando") {
            setEstado({ mensaje: "This is taking longer than usual. Try again in a few minutes." });
          } else {
            setEstado({ resultado: r });
          }
        })
        .catch((e) => vigente && setEstado({ mensaje: e.message }));
    };
    preguntar(0);
    return () => {
      vigente = false;
      clearTimeout(temporizador);
    };
  }, [catalogoId, municipio]);

  const r = estado.resultado;
  const listo = r?.estado === "listo";
  const mensaje = estado.mensaje ?? (r && !listo ? r.mensaje : null);
  const esperando = estado.cargando || estado.calculando;
  return (
    <details className="plagas">
      <summary>
        <h3>Pests and diseases</h3>
        <span className="plagas__estado">
          {esperando && "Checking…"}
          {mensaje && "Not available"}
          {listo && (
            <>
              <span className={`plaga__nivel plaga__nivel--${r.nivel}`}>{NIVEL[r.nivel]}</span> {textoResumen(r)}
            </>
          )}
        </span>
      </summary>
      <div className="plagas__cuerpo">
        {esperando && (
          <p className="plagas__aviso" aria-busy="true">
            Checking the pests of this crop against the weather here… The first check of a crop can take up to a minute.
          </p>
        )}
        {mensaje && <p className="plagas__aviso">{mensaje}</p>}
        {listo && (
          <>
            <p className="plagas__aviso">
              {r.plagas.length === 0
                ? "No pests to check for this crop in Mexico."
                : `${r.analizadas} of ${r.totalEnPais} pests present in Mexico checked · weather from ${fechaConAnio(deISO(r.ventana.desde))} to ${fechaConAnio(deISO(r.ventana.hasta))}`}
            </p>
            {r.incompleto && <p className="plagas__aviso">Some pests could not be checked right now. Try again later.</p>}
            {r.plagas.map((p) => (
              <Plaga key={p.eppocode} p={p} />
            ))}
            <small>
              EPPO Global Database, GBIF, iNaturalist and Open-Meteo. This is a risk check from the weather and public
              records, not a detection: inspect the field.
            </small>
          </>
        )}
      </div>
    </details>
  );
}
