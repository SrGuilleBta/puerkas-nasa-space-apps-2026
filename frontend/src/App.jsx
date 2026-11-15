import { useEffect, useState } from "react";
import { getParcela } from "./api/principal.js";
import EnConstruccion from "./components/EnConstruccion.jsx";
import Layout, { MUNICIPIOS } from "./components/Layout.jsx";
import useDatos from "./hooks/useDatos.js";
import Planificador from "./pages/Planificador/Planificador.jsx";
import Principal from "./pages/Principal/Principal.jsx";
import { useSeccion } from "./routes.js";

const SIN_PARCELA = { nombre: "—", hectareas: "—" };
const CLAVE_MUNICIPIO = "municipio";

// Recuerda el municipio elegido; si el almacenamiento no está disponible, no pasa nada.
function municipioGuardado() {
  try {
    const guardado = localStorage.getItem(CLAVE_MUNICIPIO);
    return MUNICIPIOS.includes(guardado) ? guardado : MUNICIPIOS[0];
  } catch {
    return MUNICIPIOS[0];
  }
}

export default function App() {
  const [municipio, setMunicipio] = useState(municipioGuardado);
  const parcela = useDatos(getParcela, []);
  const seccion = useSeccion();

  useEffect(() => {
    try {
      localStorage.setItem(CLAVE_MUNICIPIO, municipio);
    } catch {
      /* sin almacenamiento: se usa el valor por defecto la próxima vez */
    }
  }, [municipio]);

  return (
    <Layout
      seccion={seccion}
      municipio={municipio}
      onMunicipio={setMunicipio}
      parcela={parcela.datos ?? SIN_PARCELA}
    >
      {seccion.id === "principal" ? (
        <Principal municipio={municipio} />
      ) : seccion.id === "planificador" ? (
        <Planificador />
      ) : (
        <EnConstruccion nombre={seccion.nombre} />
      )}
    </Layout>
  );
}
