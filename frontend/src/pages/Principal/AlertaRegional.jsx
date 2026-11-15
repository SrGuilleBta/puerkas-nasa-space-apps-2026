import { Documento, Flecha } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { deISO, fechaCorta } from "../../utils/fechas.js";

// Último titular de News. No hay una API oficial de alertas regionales, así que esta tarjeta
// enseña la noticia más reciente (una externa si hay, si no un aviso propio) y lleva a News.
export default function AlertaRegional({ noticia }) {
  const fecha = noticia.fecha ? fechaCorta(deISO(noticia.fecha)) : null;
  return (
    <a className="alerta" href={hashDe("noticias")}>
      <span className="alerta__icono">
        <Documento size={22} />
      </span>
      <span className="alerta__cuerpo">
        <span className="alerta__etiqueta">
          Latest news · {noticia.fuente}
          {fecha && ` · ${fecha}`}
        </span>
        <strong>{noticia.titulo}</strong>
        <small>{noticia.resumen}</small>
      </span>
      <Flecha size={18} />
    </a>
  );
}
