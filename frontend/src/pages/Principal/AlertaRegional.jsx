import { Documento, Flecha } from "../../components/Iconos.jsx";

export default function AlertaRegional({ hace, titulo, detalle }) {
  return (
    <button type="button" className="alerta">
      <span className="alerta__icono">
        <Documento size={22} />
      </span>
      <span className="alerta__cuerpo">
        <span className="alerta__etiqueta">Alerta regional · hace {hace}</span>
        <strong>{titulo}</strong>
        <small>{detalle}</small>
      </span>
      <Flecha size={18} />
    </button>
  );
}
