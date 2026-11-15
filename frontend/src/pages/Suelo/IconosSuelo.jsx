// Íconos de línea del módulo Suelo, con el mismo estilo que components/Iconos.jsx (24x24, currentColor).

function Icono({ children, size = 20, ...resto }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...resto}
    >
      {children}
    </svg>
  );
}

// Terreno: dos cerros
export const Montana = (p) => (
  <Icono {...p}>
    <path d="M3 19l6-10 4 6 2-3 6 7z" />
    <path d="M9 9l1.5 2.5" />
  </Icono>
);

// Agua bajo tierra: superficie, capas y una gota abajo
export const AguaSubterranea = (p) => (
  <Icono {...p}>
    <path d="M3 6h18" />
    <path d="M3 10h4M10 10h4M17 10h4" />
    <path d="M12 13c-1.6 2.1-2.5 3.6-2.5 4.8a2.5 2.5 0 0 0 5 0c0-1.2-.9-2.7-2.5-4.8z" />
  </Icono>
);
