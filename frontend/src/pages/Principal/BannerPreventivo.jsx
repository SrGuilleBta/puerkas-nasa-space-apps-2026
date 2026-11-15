import { Alerta, Flecha } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";

export default function BannerPreventivo({ titulo, texto }) {
  return (
    <div className="banner" role="status">
      <span className="banner__icono">
        <Alerta size={18} />
      </span>
      <p className="banner__titulo">{titulo}</p>
      <p className="banner__texto">{texto}</p>
      <a className="banner__accion" href={hashDe("clima")}>
        Ver pronóstico <Flecha size={14} />
      </a>
    </div>
  );
}
