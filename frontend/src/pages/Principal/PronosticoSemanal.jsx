import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { Flecha, Gota, Lluvia, Nube, Sol, Suelo, Viento } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { etiquetaDia, mismoDia, semanaDe } from "../../utils/fechas.js";

const ICONO_CIELO = { sol: Sol, nube: Nube, lluvia: Lluvia };

function Dia({ fecha, dato, esHoy }) {
  const Cielo = ICONO_CIELO[dato.cielo];
  return (
    <li className={`dia ${esHoy ? "dia--hoy" : ""}`}>
      <span className="dia__nombre">
        {etiquetaDia(fecha)}
        {esHoy && <b className="dia__hoy">HOY</b>}
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

export default function PronosticoSemanal({ pronostico, hoy, esEjemplo }) {
  const ahora = new Date();
  const dias = semanaDe(ahora);
  const IconoHoy = ICONO_CIELO[hoy.icono] ?? Sol;

  return (
    <Tarjeta>
      <EncabezadoTarjeta
        etiqueta="Pronóstico semanal"
        titulo="Clima en tu región"
        derecha={
          <span className="insignia">
            <i /> {esEjemplo ? "DATOS DE EJEMPLO" : "DATOS REALES"}
          </span>
        }
      />

      <ol className="dias">
        {dias.map((fecha, i) => (
          <Dia key={fecha.toISOString()} fecha={fecha} dato={pronostico[i]} esHoy={mismoDia(fecha, ahora)} />
        ))}
      </ol>

      <div className="hoy">
        <div className="hoy__principal">
          <span className="hoy__icono">
            <IconoHoy size={30} />
          </span>
          <div>
            <p className="hoy__temp">{conUnidad(hoy.temperatura, "°")}</p>
            <p className="hoy__sensacion">Sensación {conUnidad(hoy.sensacion, "°")}</p>
          </div>
          <div className="hoy__cielo">
            <p>{hoy.cielo ?? "—"}</p>
            {hoy.optimoParaCampo && <span>Óptimo para campo</span>}
          </div>
          <a className="hoy__mas" href={hashDe("clima")}>
            Más detalles <Flecha size={14} />
          </a>
        </div>

        <dl className="hoy__medidas">
          <Medida icono={Gota} etiqueta="Humedad" valor={conUnidad(hoy.humedad, "%")} />
          <Medida icono={Viento} etiqueta="Viento" valor={conUnidad(hoy.vientoKmh, " km/h")} />
          <Medida icono={Suelo} etiqueta="Humedad suelo" valor={conUnidad(hoy.humedadSuelo, "%")} />
          <Medida icono={Suelo} etiqueta="pH del suelo" valor={conUnidad(hoy.phSuelo)} />
        </dl>
      </div>
    </Tarjeta>
  );
}
