import { useEffect, useId, useRef } from "react";
import { Cerrar } from "./Iconos.jsx";
import "./Dialogo.css";

// Ventana emergente. Usa el <dialog> nativo: bloquea el fondo, atrapa el foco y cierra con Esc.
// El contenido solo existe mientras está abierto, así cada vez empieza con el formulario limpio.
export default function Dialogo({ abierto, titulo, onCerrar, children }) {
  const ref = useRef(null);
  const idTitulo = useId();

  useEffect(() => {
    const el = ref.current;
    if (abierto && !el.open) el.showModal();
    if (!abierto && el.open) el.close();
  }, [abierto]);

  return (
    <dialog
      ref={ref}
      className="dialogo"
      aria-labelledby={idTitulo}
      onClose={onCerrar}
      onClick={(e) => e.target === ref.current && onCerrar()}
    >
      {abierto && (
        <div className="dialogo__cuerpo">
          <header className="dialogo__encabezado">
            <h2 id={idTitulo}>{titulo}</h2>
            <button type="button" className="dialogo__cerrar" aria-label="Close" onClick={onCerrar}>
              <Cerrar size={18} />
            </button>
          </header>
          {children}
        </div>
      )}
    </dialog>
  );
}
