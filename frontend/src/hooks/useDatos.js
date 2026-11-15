import { useCallback, useEffect, useState } from "react";

// Pide un dato y lo mantiene con su estado: { datos, cargando, error, recargar }.
// Se vuelve a pedir cuando cambia algo de `dependencias` (p. ej. el municipio) o al llamar
// `recargar()` (p. ej. después de guardar un cambio). Mientras recarga conserva los datos viejos.
export default function useDatos(pedir, dependencias = []) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: null });
  const [version, setVersion] = useState(0);
  const recargar = useCallback(() => setVersion((v) => v + 1), []);

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
  }, [...dependencias, version]);

  return { ...estado, recargar };
}
