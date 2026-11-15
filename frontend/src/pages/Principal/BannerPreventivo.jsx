import { useState } from "react";
import Dialogo from "../../components/Dialogo.jsx";
import { Alerta, Check, Flecha } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";

const NIVEL = { alta: "High", media: "Medium", baja: "Low" };

// Aviso de la semana: muestra el riesgo más importante y, si hay más, abre la lista completa.
export default function BannerPreventivo({ alertas }) {
  const [abierto, setAbierto] = useState(false);

  if (alertas.length === 0) {
    return (
      <div className="banner banner--tranquilo" role="status">
        <span className="banner__icono">
          <Check size={18} />
        </span>
        <p className="banner__titulo">No alerts right now</p>
        <p className="banner__texto">We see no weather, pest or disease risks for your crops this week.</p>
      </div>
    );
  }

  const [principal, ...otras] = alertas;
  return (
    <>
      <div className="banner" role="status">
        <span className="banner__icono">
          <Alerta size={18} />
        </span>
        <p className="banner__titulo">
          {principal.tipo === "plaga" ? "Preventive notice" : "Weather alert"} · {principal.titulo}
        </p>
        <p className="banner__texto">{principal.detalle}</p>
        <button type="button" className="banner__accion" onClick={() => setAbierto(true)}>
          {otras.length > 0 ? `View ${alertas.length} alerts` : "View details"} <Flecha size={14} />
        </button>
      </div>

      <Dialogo abierto={abierto} titulo="This week's alerts" onCerrar={() => setAbierto(false)}>
        <ul className="alertas-lista">
          {alertas.map((a) => (
            <li key={a.id} className={`alertas-lista__item alertas-lista__item--${a.nivel}`}>
              <div className="alertas-lista__cabecera">
                <b>{a.titulo}</b>
                <span>
                  {a.tipo === "plaga" ? "Plant health" : "Weather"} · {NIVEL[a.nivel]}
                </span>
              </div>
              <p>{a.detalle}</p>
              {a.cultivos.length > 0 && <small>Your crops: {a.cultivos.join(", ")}</small>}
            </li>
          ))}
        </ul>
        <p className="campo__ayuda">
          These are prompts to check your field, not detections: they are calculated from the forecast and the crops you currently have growing.
        </p>
        <div className="acciones">
          <a className="btn" href={hashDe("clima")} onClick={() => setAbierto(false)}>
            View forecast
          </a>
          <span className="acciones__espacio" />
          <button type="button" className="btn btn--primario" onClick={() => setAbierto(false)}>
            Close
          </button>
        </div>
      </Dialogo>
    </>
  );
}
