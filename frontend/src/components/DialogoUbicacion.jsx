import { useState } from "react";
import { buscarLugares, crearUbicacion } from "../api/ubicaciones.js";
import Dialogo from "./Dialogo.jsx";
import { Mas, Ubicacion } from "./Iconos.jsx";

function Formulario({ onAgregada }) {
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState(null); // null = todavía no se busca
  const [buscando, setBuscando] = useState(false);
  const [agregando, setAgregando] = useState(null); // el candidato que se está guardando
  const [error, setError] = useState(null);

  async function buscar(e) {
    e.preventDefault();
    if (texto.trim().length < 2) return setError(new Error("Escribe al menos 2 letras del lugar."));
    setBuscando(true);
    setError(null);
    try {
      setResultados(await buscarLugares(texto.trim()));
    } catch (err) {
      setError(err);
      setResultados(null);
    } finally {
      setBuscando(false);
    }
  }

  async function agregar(candidato) {
    setAgregando(candidato);
    setError(null);
    try {
      onAgregada(await crearUbicacion(candidato));
    } catch (err) {
      setError(err);
    } finally {
      setAgregando(null);
    }
  }

  return (
    <div className="formulario">
      <form className="ubic-busqueda" onSubmit={buscar} noValidate>
        <label className="campo">
          Buscar un lugar
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Ej. Guadalajara, Hermosillo, Querétaro (solo México)"
            autoFocus
            maxLength={80}
          />
        </label>
        <button type="submit" className="btn btn--primario" disabled={buscando}>
          {buscando ? "Buscando…" : "Buscar"}
        </button>
      </form>

      {error && (
        <div className="aviso aviso--error" role="alert">
          {error.message}
        </div>
      )}

      {resultados && resultados.length === 0 && (
        <p className="campo__ayuda">No encontramos ese lugar en México. Prueba con otro nombre.</p>
      )}

      {resultados && resultados.length > 0 && (
        <ul className="ubic-resultados">
          {resultados.map((r) => (
            <li key={`${r.lat},${r.lon}`}>
              <span className="ubic-resultados__icono">
                <Ubicacion size={18} />
              </span>
              <span className="ubic-resultados__texto">
                <b>{r.nombre}</b>
                <small>
                  {r.lat.toFixed(2)}, {r.lon.toFixed(2)} · {r.zona}
                </small>
              </span>
              <button type="button" className="btn" disabled={agregando !== null} onClick={() => agregar(r)}>
                <Mas size={14} /> {agregando === r ? "Agregando…" : "Agregar"}
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="campo__ayuda">
        Solo se envía lo que escribes para buscar el lugar. Después de agregarlo, el clima y el suelo se consultan para sus coordenadas.
      </p>
    </div>
  );
}

// Busca un lugar por nombre y lo agrega a la lista de ubicaciones.
export default function DialogoUbicacion({ abierto, onCerrar, onAgregada }) {
  return (
    <Dialogo abierto={abierto} titulo="Agregar ubicación" onCerrar={onCerrar}>
      <Formulario onAgregada={onAgregada} />
    </Dialogo>
  );
}
