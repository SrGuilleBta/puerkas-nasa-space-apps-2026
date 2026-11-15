import { getCondicionesLocales } from "../../api/clima.js";
import Cargable from "../../components/Cargable.jsx";
import { Brote, Gota, Lluvia, Nube, Sol, Suelo, Viento } from "../../components/Iconos.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";

const ICONO_CIELO = { sol: Sol, nube: Nube, lluvia: Lluvia };

// Muestra "—" cuando el dato no existe (null)
const con = (valor, unidad = "") => (valor == null ? "—" : `${valor}${unidad}`);

// Reglas nuestras para describir la cifra (no son categorías oficiales)
const nivelHumedad = (h) => (h == null ? null : h < 40 ? "Low level" : h <= 70 ? "Moderate level" : "High level");
const estadoSuelo = (t) => (t == null ? null : t < 10 ? "Too cold" : t <= 30 ? "Optimal condition" : "Too hot");

function Medida({ icono: Icono, etiqueta, valor, nota }) {
  return (
    <li className="condiciones__medida">
      <span className="condiciones__icono">
        <Icono size={20} />
      </span>
      <div>
        <p className="clima__etiqueta">{etiqueta}</p>
        <p className="condiciones__valor">{valor}</p>
      </div>
      {nota && <small>{nota}</small>}
    </li>
  );
}

// "Condiciones favorables" o por qué no, y hasta cuándo dura la ventana para labores de campo
function Ventana({ ventana }) {
  const { favorable, desde, hasta } = ventana;
  const texto = favorable
    ? hasta
      ? `Good window for fieldwork until ${hasta}.`
      : "Good window for fieldwork for the rest of the day."
    : desde
      ? `Not ideal for fieldwork right now. The next good window starts at ${desde}.`
      : "Not ideal for fieldwork for the rest of the day.";
  return (
    <div className={`condiciones__ventana${favorable ? "" : " condiciones__ventana--no"}`} role="status">
      <Brote size={20} />
      <div>
        <b>{favorable ? "Favorable conditions" : "Unfavorable conditions"}</b>
        <p>{texto}</p>
      </div>
    </div>
  );
}

function Contenido({ d }) {
  const Cielo = ICONO_CIELO[d.icono] ?? Sol;
  return (
    <>
      <div className="condiciones__hoy">
        <span className={`condiciones__cielo condiciones__cielo--${d.icono}`}>
          <Cielo size={28} />
        </span>
        <div>
          <p className="condiciones__temp">{con(d.temperatura, "°")}</p>
          <p className="condiciones__sensacion">
            {d.cielo ?? "—"} · Feels like {con(d.sensacion, "°")}
          </p>
          <p className="condiciones__extremos">
            High {con(d.tmax, "°")} · Low {con(d.tmin, "°")}
          </p>
        </div>
      </div>

      <ul className="condiciones__medidas">
        <Medida icono={Gota} etiqueta="Humidity" valor={con(d.humedad, "%")} nota={nivelHumedad(d.humedad)} />
        <Medida
          icono={Viento}
          etiqueta="Wind"
          valor={con(d.vientoKmh, " km/h")}
          nota={d.vientoDireccion ? `From ${d.vientoDireccion}` : null}
        />
        <Medida
          icono={Lluvia}
          etiqueta="Precipitation"
          valor={con(d.lluviaProbabilidad, "%")}
          nota={d.lluviaMm == null ? null : `${d.lluviaMm} mm expected today`}
        />
        <Medida icono={Suelo} etiqueta="Soil moisture" valor={con(d.humedadSuelo, "%")} nota="Root zone" />
        <Medida
          icono={Suelo}
          etiqueta="Soil temperature"
          valor={con(d.temperaturaSuelo, "°")}
          nota={estadoSuelo(d.temperaturaSuelo)}
        />
      </ul>

      {d.ventana && <Ventana ventana={d.ventana} />}
      <p className="clima__nota">
        Source: {d.fuente} and NASA POWER (soil moisture). The numbers match the Home screen. The fieldwork window is our
        own rule: 10–35 °C, wind under 25 km/h and under 30% chance of rain.
      </p>
    </>
  );
}

// Cómo está hoy el lugar elegido arriba: temperatura, viento, lluvia, suelo y hasta cuándo se puede trabajar
export default function CondicionesLocales({ municipio }) {
  const datos = useDatos(() => (municipio ? getCondicionesLocales(municipio) : Promise.resolve(null)), [municipio]);
  if (!municipio) return null;
  return (
    <Cargable estado={datos} alto={220}>
      {(d) => (
        <Tarjeta className="condiciones">
          <EncabezadoTarjeta etiqueta="Local conditions" titulo={d.municipio} />
          <Contenido d={d} />
        </Tarjeta>
      )}
    </Cargable>
  );
}
