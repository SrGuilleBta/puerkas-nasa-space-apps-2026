import { useMemo, useState } from "react";
import { getMapaClima } from "../../api/clima.js";
import Cargable from "../../components/Cargable.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";
import { deISO } from "../../utils/fechas.js";
import "./Clima.css";
import CondicionesLocales from "./CondicionesLocales.jsx";
import { CAPAS, textoValor, valorDe } from "./escalas.js";
import MapaMexico from "./MapaMexico.jsx";

const CAPA_TEXTOS = [
  ["lluvia", "Rain"],
  ["calor", "Heat"],
];
const DIAS_SEMANA = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const FORMATO_HORA = { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" };

function etiquetaDia(fecha, i) {
  if (i === 0) return "Today";
  if (i === 1) return "Tomorrow";
  const d = deISO(fecha);
  return `${DIAS_SEMANA[d.getDay()]} ${d.getDate()}`;
}

const etiquetaSemana = (capa) => (capa === "lluvia" ? "Week total" : "Week high");

// Barra de colores de la capa, de su valor más bajo al más alto
function Leyenda({ capa, dia }) {
  const { paradas, dominio, unidad } = CAPAS[capa];
  const [min, max] = dominio(dia);
  return (
    <div className="clima-leyenda" aria-hidden="true">
      <span>
        {min} {unidad}
      </span>
      <i style={{ background: `linear-gradient(90deg, ${paradas.join(", ")})` }} />
      <span>
        {max}+ {unidad}
      </span>
    </div>
  );
}

// Dos cifras del país en la capa y el día elegidos
function Resumen({ puntos, capa, dia }) {
  const valores = puntos.map((p) => valorDe(p, capa, dia)).filter((v) => v != null);
  if (valores.length === 0) return null;
  const max = Math.max(...valores);
  const min = Math.min(...valores);
  const con = Math.round((valores.filter((v) => v >= 1).length / valores.length) * 100);
  const media = valores.reduce((a, b) => a + b, 0) / valores.length;
  const tarjetas =
    capa === "lluvia"
      ? [
          ["Area with rain", `${con}%`, "of the map gets 1 mm or more"],
          ["Heaviest rain", textoValor(capa, max), dia === "semana" ? "in the week, at the wettest point" : "in the day, at the wettest point"],
        ]
      : [
          ["Hottest point", textoValor(capa, max), "highest maximum temperature"],
          ["Average", textoValor(capa, Math.round(media)), `across the country · coolest ${textoValor(capa, min)}`],
        ];
  return (
    <div className="clima__resumen">
      {tarjetas.map(([titulo, valor, nota]) => (
        <article key={titulo}>
          <p className="clima__etiqueta">{titulo}</p>
          <h3>{valor}</h3>
          <p>{nota}</p>
        </article>
      ))}
    </div>
  );
}

function Contenido({ datos, municipio }) {
  const [capa, setCapa] = useState("lluvia");
  const [dia, setDia] = useState(0);
  // La ubicación activa va primero en la lista
  const lugares = useMemo(
    () => datos.lugares.slice().sort((a, b) => Number(b.nombre === municipio) - Number(a.nombre === municipio)),
    [datos, municipio],
  );
  const actualizado = new Date(datos.actualizado).toLocaleString("en-US", FORMATO_HORA);
  const nombreDia = dia === "semana" ? etiquetaSemana(capa).toLowerCase() : etiquetaDia(datos.dias[dia], dia).toLowerCase();

  return (
    <>
      <Tarjeta>
        <EncabezadoTarjeta
          etiqueta="National monitoring"
          titulo="Weather map of Mexico"
          derecha={
            <div className="clima__capas" role="tablist" aria-label="Map layer">
              {CAPA_TEXTOS.map(([id, texto]) => (
                <button key={id} type="button" role="tab" aria-selected={capa === id} onClick={() => setCapa(id)}>
                  {texto}
                </button>
              ))}
            </div>
          }
        />
        <div className="clima__dias" role="tablist" aria-label="Day">
          {datos.dias.map((fecha, i) => (
            <button key={fecha} type="button" role="tab" aria-selected={dia === i} onClick={() => setDia(i)}>
              {etiquetaDia(fecha, i)}
            </button>
          ))}
          <button type="button" role="tab" aria-selected={dia === "semana"} onClick={() => setDia("semana")}>
            {etiquetaSemana(capa)}
          </button>
        </div>
        {datos.desactualizado && (
          <p className="aviso aviso--info" role="status">
            The weather service did not answer, so this map shows the last forecast we had (from {actualizado}).
          </p>
        )}
        <MapaMexico datos={datos} capa={capa} dia={dia} />
        <Leyenda capa={capa} dia={dia} />
        <p className="clima__nota">
          {capa === "lluvia"
            ? `Forecast rain ${dia === "semana" ? "added up over the 7 days" : "for the day"}, in millimeters. Areas without color get less than 0.2 mm.`
            : dia === "semana"
              ? "Highest maximum temperature forecast in the 7 days, in °C."
              : "Forecast maximum temperature for the day, in °C. Redder means hotter."}
        </p>
        <Resumen puntos={datos.puntos} capa={capa} dia={dia} />
      </Tarjeta>

      {lugares.length > 0 && (
        <Tarjeta>
          <EncabezadoTarjeta etiqueta="Your places" titulo={`${capa === "lluvia" ? "Rain" : "Heat"} · ${nombreDia}`} />
          <ul className="clima__lugares">
            {lugares.map((l) => (
              <li key={l.nombre} className={l.nombre === municipio ? "clima__lugar--activo" : ""}>
                <span>{l.nombre}</span>
                <b>{textoValor(capa, valorDe(l, capa, dia))}</b>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}

      <p className="clima__nota">
        Source: {datos.fuente} forecast (model values on a grid of {datos.puntos.length} points about {Math.round(datos.paso * 111)} km apart),
        updated {actualizado} and refreshed every 3 hours. It shows the regional pattern, not how much rain falls on your field.
        Observed rain from NASA POWER is in the Crop guide of the Planner.
      </p>
    </>
  );
}

// Pantalla Weather: mapa de México con la lluvia pronosticada y el calor (temperatura máxima), por día o de la semana.
export default function Clima({ municipio }) {
  const mapa = useDatos(getMapaClima, []);
  return (
    <div className="clima">
      <h1 className="sr-only">Weather</h1>
      <CondicionesLocales municipio={municipio} />
      <Cargable estado={mapa} alto={420}>
        {(datos) => <Contenido datos={datos} municipio={municipio} />}
      </Cargable>
    </div>
  );
}
