// Iconos de línea (24x24). Heredan el color con currentColor.
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

export const Menu = (p) => (
  <Icono {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icono>
);
export const Cerrar = (p) => (
  <Icono {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Icono>
);
export const Sol = (p) => (
  <Icono {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Icono>
);
export const Nube = (p) => (
  <Icono {...p}>
    <path d="M7 18a4 4 0 0 1-.6-7.96A5.5 5.5 0 0 1 17 9.5a4.25 4.25 0 0 1 0 8.5H7z" />
  </Icono>
);
export const Lluvia = (p) => (
  <Icono {...p}>
    <path d="M7 15a4 4 0 0 1-.6-7.96A5.5 5.5 0 0 1 17 6.5a4.25 4.25 0 0 1 0 8.5" />
    <path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3" />
  </Icono>
);
export const Gota = (p) => (
  <Icono {...p}>
    <path d="M12 3s6 6.2 6 10.5A6 6 0 0 1 6 13.5C6 9.2 12 3 12 3z" />
  </Icono>
);
export const Viento = (p) => (
  <Icono {...p}>
    <path d="M3 9h11a3 3 0 1 0-3-3M3 15h15a3 3 0 1 1-3 3M3 12h8" />
  </Icono>
);
export const Suelo = (p) => (
  <Icono {...p}>
    <rect x="3" y="5" width="18" height="14" rx="3" />
    <path d="M3 11h18M8 11v8M15 11v8" />
  </Icono>
);
export const Alerta = (p) => (
  <Icono {...p}>
    <path d="M12 3.5L2.5 20h19L12 3.5z" />
    <path d="M12 10v4.5M12 17.5v.01" />
  </Icono>
);
export const Documento = (p) => (
  <Icono {...p}>
    <rect x="5" y="3" width="14" height="18" rx="2.5" />
    <path d="M9 8h6M9 12h6M9 16h4" />
  </Icono>
);
export const Brote = (p) => (
  <Icono {...p}>
    <path d="M12 21v-9" />
    <path d="M12 12C12 8 9 5.5 4.5 5.5 4.5 10 7.5 12 12 12z" />
    <path d="M12 14c0-3.2 2.4-5.5 7-5.5 0 4-2.8 5.5-7 5.5z" />
  </Icono>
);
export const Tendencia = (p) => (
  <Icono {...p}>
    <path d="M3 17l6-6 4 4 8-8" />
    <path d="M15 7h6v6" />
  </Icono>
);
export const Mas = (p) => (
  <Icono {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icono>
);
export const Menos = (p) => (
  <Icono {...p}>
    <path d="M5 12h14" />
  </Icono>
);
export const Flecha = (p) => (
  <Icono {...p}>
    <path d="M9 6l6 6-6 6" />
  </Icono>
);
export const Lapiz = (p) => (
  <Icono {...p}>
    <path d="M4 20l4-1 11-11a2.1 2.1 0 0 0-3-3L5 16l-1 4z" />
  </Icono>
);
export const Calendario = (p) => (
  <Icono {...p}>
    <rect x="3.5" y="5" width="17" height="15" rx="3" />
    <path d="M3.5 10h17M8 3v4M16 3v4" />
  </Icono>
);
export const Ubicacion = (p) => (
  <Icono {...p}>
    <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" />
    <circle cx="12" cy="10" r="2.3" />
  </Icono>
);
export const Check = (p) => (
  <Icono {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Icono>
);
export const Abajo = (p) => (
  <Icono {...p}>
    <path d="M6 9l6 6 6-6" />
  </Icono>
);
