import "./Tarjeta.css";

// Contenedor de cristal que usan todas las secciones de las pantallas.
export default function Tarjeta({ children, className = "", ...resto }) {
  return (
    <section className={`tarjeta ${className}`} {...resto}>
      {children}
    </section>
  );
}

export function EncabezadoTarjeta({ etiqueta, titulo, derecha }) {
  return (
    <header className="tarjeta__encabezado">
      <div>
        <p className="tarjeta__etiqueta">{etiqueta}</p>
        {titulo && <h2 className="tarjeta__titulo">{titulo}</h2>}
      </div>
      {derecha}
    </header>
  );
}
