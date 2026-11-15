import { useEffect, useState } from "react";

// Pantallas de la app. `hash` es lo que va en la dirección: http://localhost:8000/#/clima
// Se usa hash para que refrescar funcione tanto en desarrollo como en la imagen de producción.
export const SECCIONES = [
  { id: "principal", nombre: "Principal", hash: "#/" },
  { id: "clima", nombre: "Clima", hash: "#/clima" },
  { id: "suelo", nombre: "Suelo", hash: "#/suelo" },
  { id: "mercado", nombre: "Mercado", hash: "#/mercado" },
  { id: "cultivos", nombre: "Cultivos", hash: "#/cultivos" },
  { id: "planificador", nombre: "Planificador", hash: "#/planificador" },
  { id: "noticias", nombre: "Noticias", hash: "#/noticias" },
];

export const hashDe = (id) => SECCIONES.find((s) => s.id === id).hash;

const seccionActual = () =>
  SECCIONES.find((s) => s.hash === window.location.hash) ??
  SECCIONES.find((s) => s.id === "principal");

// Devuelve la sección activa y se actualiza cuando cambia la dirección.
export function useSeccion() {
  const [seccion, setSeccion] = useState(seccionActual);

  useEffect(() => {
    const alCambiar = () => {
      setSeccion(seccionActual());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);

  return seccion;
}
