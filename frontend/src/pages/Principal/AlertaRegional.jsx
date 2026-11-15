import { Documento, Flecha } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";

export default function AlertaRegional({ hace, titulo, detalle }) {
  return (
    <a className="alerta" href={hashDe("noticias")}>
      <span className="alerta__icono">
        <Documento size={22} />
      </span>
      <span className="alerta__cuerpo">
        <span className="alerta__etiqueta">Regional alert · {hace} ago</span>
        <strong>{titulo}</strong>
        <small>{detalle}</small>
      </span>
      <Flecha size={18} />
    </a>
  );
}
