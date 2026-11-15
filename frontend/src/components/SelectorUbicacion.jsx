import { useEffect, useRef, useState } from "react";
import { borrarUbicacion } from "../api/ubicaciones.js";
import DialogoUbicacion from "./DialogoUbicacion.jsx";
import { Abajo, Cerrar, Check, Mas, Ubicacion } from "./Iconos.jsx";
import "./SelectorUbicacion.css";

// Selector de ubicación del encabezado: muestra el lugar actual y abre un menú con los lugares
// guardados, "Usar mi ubicación" (la del navegador, pide permiso) y "Agregar ubicación".
//  - onElegir(nombre): cambia el lugar activo
//  - onUsarMiUbicacion(): async; debe lanzar un Error con un mensaje legible si no se pudo
//  - onCambio(nombreAElegir?): la lista cambió (se agregó o quitó algo) y hay que recargarla
export default function SelectorUbicacion({ ubicaciones, elegida, onElegir, onUsarMiUbicacion, onCambio }) {
  const [abierto, setAbierto] = useState(false);
  const [agregando, setAgregando] = useState(false);
  const [buscandoMia, setBuscandoMia] = useState(false);
  const [aviso, setAviso] = useState(null);
  const raiz = useRef(null);

  // Cerrar el menú al hacer clic fuera o con Esc
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e) => !raiz.current.contains(e.target) && setAbierto(false);
    const tecla = (e) => e.key === "Escape" && setAbierto(false);
    document.addEventListener("pointerdown", fuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("pointerdown", fuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  function elegir(nombre) {
    onElegir(nombre);
    setAbierto(false);
  }

  async function usarMia() {
    setBuscandoMia(true);
    setAviso(null);
    try {
      await onUsarMiUbicacion();
      setAbierto(false);
    } catch (e) {
      setAviso(e.message);
    } finally {
      setBuscandoMia(false);
    }
  }

  async function quitar(u) {
    setAviso(null);
    try {
      await borrarUbicacion(u.id);
      onCambio();
    } catch (e) {
      setAviso(e.message);
    }
  }

  const unica = ubicaciones.length <= 1;

  return (
    <div className="ubic" ref={raiz}>
      <button
        type="button"
        className="ubic__boton"
        aria-haspopup="true"
        aria-expanded={abierto}
        aria-label={`Ubicación: ${elegida}. Cambiar`}
        onClick={() => {
          setAbierto((a) => !a);
          setAviso(null);
        }}
      >
        <Ubicacion size={16} />
        <span className="ubic__nombre">{elegida}</span>
        <Abajo size={14} />
      </button>

      {abierto && (
        <div className="ubic__panel" role="group" aria-label="Ubicaciones">
          <ul className="ubic__lista">
            {ubicaciones.map((u) => (
              <li key={u.id} className="ubic__fila">
                <button
                  type="button"
                  className={`ubic__opcion ${u.nombre === elegida ? "ubic__opcion--actual" : ""}`}
                  aria-current={u.nombre === elegida ? "true" : undefined}
                  onClick={() => elegir(u.nombre)}
                >
                  <span className="ubic__marca">{u.nombre === elegida && <Check size={14} />}</span>
                  {u.nombre}
                </button>
                {!unica && (
                  <button type="button" className="ubic__quitar" aria-label={`Quitar ${u.nombre}`} title="Quitar de la lista" onClick={() => quitar(u)}>
                    <Cerrar size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>

          <div className="ubic__acciones">
            <button type="button" className="ubic__accion" disabled={buscandoMia} onClick={usarMia}>
              <Ubicacion size={16} /> {buscandoMia ? "Buscando tu ubicación…" : "Usar mi ubicación"}
            </button>
            <button
              type="button"
              className="ubic__accion"
              onClick={() => {
                setAbierto(false);
                setAgregando(true);
              }}
            >
              <Mas size={16} /> Agregar ubicación…
            </button>
          </div>

          {aviso && (
            <p className="ubic__aviso" role="alert">
              {aviso}
            </p>
          )}
        </div>
      )}

      <DialogoUbicacion
        abierto={agregando}
        onCerrar={() => setAgregando(false)}
        onAgregada={(nueva) => {
          setAgregando(false);
          onCambio(nueva.nombre);
        }}
      />
    </div>
  );
}
