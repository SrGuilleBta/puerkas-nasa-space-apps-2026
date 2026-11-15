import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { Flecha, Gota, Lluvia, Nube, Sol, Suelo, Viento } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { deISO, etiquetaDia, mismoDia } from "../../utils/fechas.js";

const ICONO_CIELO = { sol: Sol, nube: Nube, lluvia: Lluvia };

function Dia({ fecha, dato, esHoy }) {
  const Cielo = ICONO_CIELO[dato.cielo];
  return (
    <li className={`dia ${esHoy ? "dia--hoy" : ""}`}>
      <span className="dia__nombre">
        {etiquetaDia(fecha)}
        {esHoy && <b className="dia__hoy">TODAY</b>}
      </span>
      <span className={`dia__cielo dia__cielo--${dato.cielo}`}>
        <Cielo size={22} />
      </span>
      <span className="dia__temp">{dato.tmax == null ? "—" : `${dato.tmax}°`}</span>
      <span className="dia__lluvia">
        <Gota size={12} />
        {dato.lluvia == null ? "—" : `${dato.lluvia}%`}
      </span>
    </li>
  );
}

// Muestra "—" cuando el dato todavía no existe (valor null).
const conUnidad = (valor, unidad = "") => (valor == null ? "—" : `${valor}${unidad}`);

function Medida({ icono: Icono, etiqueta, valor }) {
  return (
    <div className="medida">
      <Icono size={20} />
      <div>
        <dt>{etiqueta}</dt>
        <dd>{valor}</dd>
      </div>
    </div>
  );
}

export default function PronosticoSemanal({ pronostico, hoy, fuente }) {
  // El primer día es hoy: si llegara algún día anterior (respuesta vieja), se descarta. Los datos de
  // ejemplo no traen fecha: se cuentan desde hoy.
  const ahora = new Date();
  const inicioHoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());
  const dias = pronostico
    .map((d, i) => {
      if (d.fecha) return { fecha: deISO(d.fecha), dato: d };
      const f = new Date(inicioHoy);
      f.setDate(f.getDate() + i);
      return { fecha: f, dato: d };
    })
    .filter((x) => x.fecha >= inicioHoy);
  const IconoHoy = ICONO_CIELO[hoy.icono] ?? Sol;

  return (
    <Tarjeta>
      <EncabezadoTarjeta
        etiqueta="7-day forecast"
        titulo="Weather in your region"
        derecha={
          <span className="insignia">
            <i /> LIVE DATA{fuente ? ` · ${fuente}` : ""}
          </span>
        }
      />

      <ol className="dias">
        {dias.map(({ fecha, dato }) => (
          <Dia key={fecha.toISOString()} fecha={fecha} dato={dato} esHoy={mismoDia(fecha, ahora)} />
        ))}
      </ol>

      <div className="hoy">
        <div className="hoy__principal">
          <span className="hoy__icono">
            <IconoHoy size={30} />
          </span>
          <div>
            <p className="hoy__temp">{conUnidad(hoy.temperatura, "°")}</p>
            <p className="hoy__sensacion">Feels like {conUnidad(hoy.sensacion, "°")}</p>
          </div>
          <div className="hoy__cielo">
            <p>{hoy.cielo ?? "—"}</p>
            {hoy.optimoParaCampo && <span>Good for fieldwork</span>}
          </div>
          <a className="hoy__mas" href={hashDe("clima")}>
            More details <Flecha size={14} />
          </a>
        </div>

        <dl className="hoy__medidas">
          <Medida icono={Gota} etiqueta="Humidity" valor={conUnidad(hoy.humedad, "%")} />
          <Medida icono={Viento} etiqueta="Wind" valor={conUnidad(hoy.vientoKmh, " km/h")} />
          <Medida icono={Suelo} etiqueta="Soil moisture" valor={conUnidad(hoy.humedadSuelo, "%")} />
          <Medida icono={Suelo} etiqueta="Soil pH" valor={conUnidad(hoy.phSuelo)} />
        </dl>
      </div>
    </Tarjeta>
  );
}
