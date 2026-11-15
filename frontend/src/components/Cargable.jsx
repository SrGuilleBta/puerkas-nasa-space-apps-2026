import Tarjeta from "./Tarjeta.jsx";

// Muestra una tarjeta de carga o de error mientras el dato no está listo y,
// cuando llega, pinta `children(datos)`. Así cada sección se carga por separado.
export default function Cargable({ estado, alto = 160, children }) {
  if (estado.error) {
    return (
      <Tarjeta className="estado estado--error" role="alert">
        <p>No se pudo cargar esta sección.</p>
        <small>{estado.error.message}</small>
      </Tarjeta>
    );
  }
  if (!estado.datos) {
    return (
      <Tarjeta
        className="estado estado--cargando"
        style={{ minHeight: alto }}
        aria-busy="true"
        aria-label="Cargando"
      />
    );
  }
  return children(estado.datos);
}
