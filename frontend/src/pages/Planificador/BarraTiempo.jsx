import { useEffect, useRef } from "react";
import { finVentana } from "../../utils/ventana.js";

const limitar = (n, min, max) => Math.min(max, Math.max(min, n));
const ESPERA_REPETIR = 350; // ms con la flecha presionada antes de que empiece a repetirse
const CADA = 60; // ms entre cada repetición

function Triangulo({ hacia }) {
  return (
    <svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true">
      <path d={hacia === "izquierda" ? "M7 0 L7 8 L0 4 Z" : "M1 0 L1 8 L8 4 Z"} fill="currentColor" />
    </svg>
  );
}

// Barra de desplazamiento horizontal del calendario, al estilo clásico: flecha en cada extremo,
// pista clara y manija gris. La pista representa todo el tramo del plan y la manija es lo que se
// está viendo. Se arrastra la manija, se toca la pista para saltar, las flechas mueven poco a poco
// (y se repiten si se mantienen presionadas) y con el teclado se usan ← → AvPág RePág e Inicio.
export default function BarraTiempo({ ventana, rango, controla, onMoverA, onDesplazar, onHoy }) {
  const pista = useRef(null);
  const arrastre = useRef(null); // { id, x, inicio } mientras se arrastra
  const repeticion = useRef({}); // temporizadores de las flechas
  const ultimo = useRef({});
  ultimo.current = { onDesplazar };

  const dur = finVentana(ventana) - ventana.inicio;
  // Que el tramo sea al menos el doble de la ventana; si no, la manija ocuparía casi toda la pista
  let desde = rango.inicio.getTime();
  let hasta = rango.fin.getTime();
  if (hasta - desde < 2 * dur) {
    const extra = (2 * dur - (hasta - desde)) / 2;
    desde -= extra;
    hasta += extra;
  }
  const total = hasta - desde;

  const ancho = (dur / total) * 100;
  const izquierda = limitar(((ventana.inicio.getTime() - desde) / total) * 100, 0, 100 - ancho);
  const avance = ancho >= 100 ? 0 : Math.round((izquierda / (100 - ancho)) * 100);

  const anchoPista = () => pista.current.getBoundingClientRect().width || 1;

  // ---- Pista y manija ----
  function alPresionar(e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    let inicio = ventana.inicio.getTime();
    if (!e.target.closest(".tiempo__manija")) {
      // Toque en la pista: la manija salta ahí (centrada) y de ahí se puede seguir arrastrando
      const x = e.clientX - pista.current.getBoundingClientRect().left;
      inicio = desde + (x / anchoPista()) * total - dur / 2;
      onMoverA(new Date(inicio));
    }
    arrastre.current = { id: e.pointerId, x: e.clientX, inicio };
    pista.current.setPointerCapture(e.pointerId);
  }

  function alMover(e) {
    const a = arrastre.current;
    if (!a || a.id !== e.pointerId) return;
    onMoverA(new Date(a.inicio + ((e.clientX - a.x) / anchoPista()) * total));
  }

  const alSoltar = () => {
    arrastre.current = null;
  };

  // ---- Flechas: un paso de ~1 semana, que se repite si se mantiene presionada ----
  const paso = (7 / (ventana.meses * 30.4375)) * 1;
  function empezarFlecha(sentido, e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    detenerFlecha();
    ultimo.current.onDesplazar(sentido * paso);
    repeticion.current.espera = setTimeout(() => {
      repeticion.current.cada = setInterval(() => ultimo.current.onDesplazar(sentido * paso), CADA);
    }, ESPERA_REPETIR);
  }
  function detenerFlecha() {
    clearTimeout(repeticion.current.espera);
    clearInterval(repeticion.current.cada);
  }
  useEffect(() => detenerFlecha, []); // al salir de la pantalla no debe quedar nada corriendo

  function alTeclear(e) {
    const mes = dur / ventana.meses;
    const ini = ventana.inicio.getTime();
    if (e.key === "ArrowLeft") onMoverA(new Date(ini - mes));
    else if (e.key === "ArrowRight") onMoverA(new Date(ini + mes));
    else if (e.key === "PageUp") onMoverA(new Date(ini - dur / 2));
    else if (e.key === "PageDown") onMoverA(new Date(ini + dur / 2));
    else if (e.key === "Home") onHoy();
    else return;
    e.preventDefault();
  }

  return (
    <div className="tiempo">
      <button
        type="button"
        className="tiempo__flecha"
        aria-label="Move calendar backward"
        tabIndex={-1}
        onPointerDown={(e) => empezarFlecha(-1, e)}
        onPointerUp={detenerFlecha}
        onPointerLeave={detenerFlecha}
        onPointerCancel={detenerFlecha}
        onKeyDown={(e) => e.key === "Enter" && onDesplazar(-paso * 4)}
      >
        <Triangulo hacia="izquierda" />
      </button>

      <div
        ref={pista}
        className="tiempo__pista"
        onPointerDown={alPresionar}
        onPointerMove={alMover}
        onPointerUp={alSoltar}
        onPointerCancel={alSoltar}
      >
        <span
          className="tiempo__manija"
          style={{ left: `${izquierda}%`, width: `${ancho}%` }}
          role="scrollbar"
          aria-label="Move calendar through time"
          aria-orientation="horizontal"
          aria-controls={controla}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={avance}
          tabIndex={0}
          onKeyDown={alTeclear}
        />
      </div>

      <button
        type="button"
        className="tiempo__flecha"
        aria-label="Move calendar forward"
        tabIndex={-1}
        onPointerDown={(e) => empezarFlecha(1, e)}
        onPointerUp={detenerFlecha}
        onPointerLeave={detenerFlecha}
        onPointerCancel={detenerFlecha}
        onKeyDown={(e) => e.key === "Enter" && onDesplazar(paso * 4)}
      >
        <Triangulo hacia="derecha" />
      </button>
    </div>
  );
}
