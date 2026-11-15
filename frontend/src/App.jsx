import { useEffect, useState } from "react";
import { guardarMiUbicacion, listarUbicaciones } from "./api/ubicaciones.js";
import Cargable from "./components/Cargable.jsx";
import EnConstruccion from "./components/EnConstruccion.jsx";
import Layout from "./components/Layout.jsx";
import SelectorUbicacion from "./components/SelectorUbicacion.jsx";
import useDatos from "./hooks/useDatos.js";
import Noticias from "./pages/Noticias/Noticias.jsx";
import Planificador from "./pages/Planificador/Planificador.jsx";
import Principal from "./pages/Principal/Principal.jsx";
import Suelo from "./pages/Suelo/Suelo.jsx";
import { useSeccion } from "./routes.js";

const CLAVE_UBICACION = "municipio"; // se conserva el nombre de la clave de cuando eran 4 municipios fijos
const CLAVE_PREGUNTADA = "ubicacionPreguntada";

// Lee y escribe en localStorage sin romper si el navegador lo bloquea.
const leer = (clave) => {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
};
const guardar = (clave, valor) => {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    /* sin almacenamiento: se usan los valores por defecto la próxima vez */
  }
};

const MENSAJE_GEOLOCALIZACION = {
  1: "Location permission was denied. You can enable it in your browser settings.",
  2: "Your location could not be determined.",
  3: "Getting your location took too long. Please try again.",
};

// Pide la ubicación al navegador (que pregunta al usuario). Rechaza con un Error legible.
function obtenerPosicion() {
  return new Promise((resolver, rechazar) => {
    if (!navigator.geolocation) return rechazar(new Error("Your browser does not support geolocation."));
    navigator.geolocation.getCurrentPosition(resolver, (e) => rechazar(new Error(MENSAJE_GEOLOCALIZACION[e.code] ?? "Could not get your location.")), {
      timeout: 10000,
      maximumAge: 600000,
    });
  });
}

// Coordenadas con 3 decimales (~110 m): suficiente para el clima y no guarda de más.
const redondear = (n) => Math.round(n * 1000) / 1000;

export default function App() {
  const ubicaciones = useDatos(listarUbicaciones, []);
  const [elegida, setElegida] = useState(() => leer(CLAVE_UBICACION));
  const seccion = useSeccion();

  const lista = ubicaciones.datos ?? [];
  // El lugar activo: el guardado y, si ya no existe (se quitó), el primero de la lista
  const activa = lista.find((u) => u.nombre === elegida) ?? lista[0] ?? null;

  useEffect(() => {
    if (activa) guardar(CLAVE_UBICACION, activa.nombre);
  }, [activa?.nombre]);

  // Guarda las coordenadas del navegador como "Mi ubicación" y la activa.
  async function usarMiUbicacion() {
    const { coords } = await obtenerPosicion();
    const zona = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const mia = await guardarMiUbicacion({ lat: redondear(coords.latitude), lon: redondear(coords.longitude), zona });
    ubicaciones.recargar();
    setElegida(mia.nombre);
  }

  // La primera vez que se abre la app se ofrece detectar la ubicación (el navegador pide permiso).
  // Solo una vez: si se niega o falla, no se vuelve a preguntar; queda el botón del selector.
  // Si el almacenamiento no funciona no se pregunta, para no pedir permiso en cada recarga.
  useEffect(() => {
    if (leer(CLAVE_PREGUNTADA) !== null) return;
    guardar(CLAVE_PREGUNTADA, "1");
    if (leer(CLAVE_PREGUNTADA) === null) return;
    usarMiUbicacion().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function alCambiarLista(nombreAElegir) {
    ubicaciones.recargar();
    if (nombreAElegir) setElegida(nombreAElegir);
  }

  return (
    <Layout
      seccion={seccion}
      selector={
        activa && (
          <SelectorUbicacion
            ubicaciones={lista}
            elegida={activa.nombre}
            onElegir={setElegida}
            onUsarMiUbicacion={usarMiUbicacion}
            onCambio={alCambiarLista}
          />
        )
      }
    >
      {seccion.id === "principal" ? (
        <Cargable estado={ubicaciones} alto={200}>
          {() => activa && <Principal municipio={activa.nombre} />}
        </Cargable>
      ) : seccion.id === "planificador" ? (
        <Planificador municipio={activa?.nombre} />
      ) : seccion.id === "suelo" ? (
        <Cargable estado={ubicaciones} alto={200}>
          {() => activa && <Suelo ubicacion={activa} />}
        </Cargable>
      ) : seccion.id === "noticias" ? (
        activa && <Noticias municipio={activa.nombre} />
      ) : (
        <EnConstruccion nombre={seccion.nombre} />
      )}
    </Layout>
  );
}
