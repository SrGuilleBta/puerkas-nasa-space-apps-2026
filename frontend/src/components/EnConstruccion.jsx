import { hashDe } from "../routes.js";
import Tarjeta from "./Tarjeta.jsx";
import { Brote, Flecha } from "./Iconos.jsx";
import "./EnConstruccion.css";

// Marcador para las pantallas que todavía no existen.
export default function EnConstruccion({ nombre }) {
  return (
    <Tarjeta className="construccion">
      <span className="construccion__icono">
        <Brote size={28} />
      </span>
      <h1>{nombre}</h1>
      <p>This screen is still under construction.</p>
      <a className="boton-principal construccion__volver" href={hashDe("principal")}>
        Back to Home <Flecha size={16} />
      </a>
    </Tarjeta>
  );
}
