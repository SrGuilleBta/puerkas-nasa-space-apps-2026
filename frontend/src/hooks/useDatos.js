import { useEffect, useState } from "react";

// Pide un dato y lo mantiene con su estado: { datos, cargando, error }.
// Se vuelve a pedir cuando cambia algo de `dependencias` (p. ej. el municipio).
export default function useDatos(pedir, dependencias = []) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: null });

  useEffect(() => {
    let vigente = true;
    setEstado((previo) => ({ ...previo, cargando: true, error: null }));
    pedir()
      .then((datos) => vigente && setEstado({ datos, cargando: false, error: null }))
      .catch((error) => vigente && setEstado({ datos: null, cargando: false, error }));
    return () => {
      vigente = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias);

  return estado;
}
