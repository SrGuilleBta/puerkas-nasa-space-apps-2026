import { Alerta, Flecha } from "../../components/Iconos.jsx";

export default function BannerPreventivo({ titulo, texto }) {
  return (
    <div className="banner" role="status">
      <span className="banner__icono">
        <Alerta size={18} />
      </span>
      <p className="banner__titulo">{titulo}</p>
      <p className="banner__texto">{texto}</p>
      <button type="button" className="banner__accion">
        Ver pronóstico <Flecha size={14} />
      </button>
    </div>
  );
}
