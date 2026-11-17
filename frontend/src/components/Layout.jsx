import { useEffect, useState } from "react";
import { obtener } from "../api/cliente.js";
import { SECCIONES } from "../routes.js";
import { Brote, Cerrar, Menu } from "./Iconos.jsx";
import PlanLateral from "./PlanLateral.jsx";
import "./Layout.css";

// `selector` es lo que va a la derecha del encabezado (el selector de ubicación).
export default function Layout({ seccion, selector, children }) {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [soloLectura, setSoloLectura] = useState(false);

  // Si el servidor es una demo de solo lectura se avisa, para que nadie piense que los botones están rotos
  useEffect(() => {
    obtener("/api/health").then((s) => setSoloLectura(Boolean(s?.readOnly))).catch(() => {});
  }, []);

  useEffect(() => {
    if (!menuAbierto) return;
    const alTeclear = (e) => e.key === "Escape" && setMenuAbierto(false);
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [menuAbierto]);

  return (
    <div className="layout">
      {soloLectura && (
        <p className="layout__demo" role="status">
          Read-only demo: you can explore everything, but changes (plans, plantings, places) are disabled.
        </p>
      )}
      <header className="layout__barra">
        <button
          type="button"
          className="layout__menu"
          aria-label="Open menu"
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
        aria-label="Sections"
        aria-hidden={!menuAbierto}
      >
        <button
          type="button"
          className="layout__cerrar"
          aria-label="Close menu"
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

        <PlanLateral abierto={menuAbierto} />
      </nav>
    </div>
  );
}
