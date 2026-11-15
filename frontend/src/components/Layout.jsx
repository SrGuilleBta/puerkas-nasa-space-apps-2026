import { useEffect, useState } from "react";
import { SECCIONES } from "../routes.js";
import { Brote, Cerrar, Menu } from "./Iconos.jsx";
import "./Layout.css";

// `selector` es lo que va a la derecha del encabezado (el selector de ubicación).
export default function Layout({ seccion, selector, parcela, children }) {
  const [menuAbierto, setMenuAbierto] = useState(false);

  useEffect(() => {
    if (!menuAbierto) return;
    const alTeclear = (e) => e.key === "Escape" && setMenuAbierto(false);
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [menuAbierto]);

  return (
    <div className="layout">
      <header className="layout__barra">
        <button
          type="button"
          className="layout__menu"
          aria-label="Abrir menú"
          aria-expanded={menuAbierto}
          onClick={() => setMenuAbierto(true)}
        >
          <Menu />
        </button>

        <div className="layout__marca">
          <span className="layout__logo">
            <Brote size={18} />
          </span>
          <span className="layout__nombre">
            Cro<span>Pro</span>
          </span>
          <span className="layout__beta">beta</span>
        </div>

        <div className="layout__selector">{selector}</div>
      </header>

      <main className="layout__contenido">{children}</main>

      {menuAbierto && (
        <div className="layout__fondo" onClick={() => setMenuAbierto(false)} />
      )}
      <nav
        className={`layout__lateral ${menuAbierto ? "layout__lateral--abierto" : ""}`}
        aria-label="Secciones"
        aria-hidden={!menuAbierto}
      >
        <button
          type="button"
          className="layout__cerrar"
          aria-label="Cerrar menú"
          tabIndex={menuAbierto ? 0 : -1}
          onClick={() => setMenuAbierto(false)}
        >
          <Cerrar />
        </button>

        <ul>
          {SECCIONES.map((s) => {
            const activa = s.id === seccion.id;
            return (
              <li key={s.id}>
                <a
                  href={s.hash}
                  className={`layout__enlace ${activa ? "layout__enlace--activo" : ""}`}
                  tabIndex={menuAbierto ? 0 : -1}
                  aria-current={activa ? "page" : undefined}
                  onClick={() => setMenuAbierto(false)}
                >
                  {s.nombre}
                </a>
              </li>
            );
          })}
        </ul>

        <div className="layout__parcela">
          <p>Mi parcela</p>
          <strong>{parcela.nombre}</strong>
          <span>{parcela.hectareas} ha</span>
        </div>
      </nav>
    </div>
  );
}
