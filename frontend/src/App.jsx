import { useState } from "react";
import { getParcela } from "./api/principal.js";
import Layout, { MUNICIPIOS } from "./components/Layout.jsx";
import useDatos from "./hooks/useDatos.js";
import Principal from "./pages/Principal/Principal.jsx";

const SIN_PARCELA = { nombre: "—", hectareas: "—" };

export default function App() {
  const [municipio, setMunicipio] = useState(MUNICIPIOS[0]);
  const parcela = useDatos(getParcela, []);

  return (
    <Layout
      municipio={municipio}
      onMunicipio={setMunicipio}
      parcela={parcela.datos ?? SIN_PARCELA}
    >
      <Principal municipio={municipio} />
    </Layout>
  );
}
