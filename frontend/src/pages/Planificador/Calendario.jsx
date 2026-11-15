import { useEffect, useRef, useState } from "react";
import { Lapiz, Mas } from "../../components/Iconos.jsx";
import { colorCultivo } from "../../utils/colores.js";
import { deISO, fechaCorta, sumarDias } from "../../utils/fechas.js";
import { mesesDeVentana, posicion } from "../../utils/ventana.js";

// Fondo neutro de la pista: una línea tenue al inicio de cada mes y la línea de "hoy".
// Los colores quedan solo para las barras de los cultivos.
function Fondo({ ventana, hoy }) {
  const ahora = posicion(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate(), 12), ventana);
  return (
    <>
      {mesesDeVentana(ventana)
        .filter((m) => m.izquierda > 0 && m.izquierda < 100)
        .map((m) => (
          <span key={m.clave} className="cal__linea" style={{ left: `${m.izquierda}%` }} />
        ))}
      {ahora >= 0 && ahora <= 100 && <span className="cal__hoy" style={{ left: `${ahora}%` }} />}
    </>
  );
}

function Barra({ siembra, ventana, onEditar }) {
  const inicio = deISO(siembra.fechaSiembra);
  const fin = deISO(siembra.fechaCosecha);
  // El día de cosecha cuenta completo, por eso la barra termina al final de ese día.
  let izquierda = posicion(inicio, ventana);
  let derecha = posicion(sumarDias(fin, 1), ventana);
  if (derecha <= 0 || izquierda >= 100) return null; // fuera de la ventana
  const seSaleIzquierda = izquierda < 0;
  const seSaleDerecha = derecha > 100;
  izquierda = Math.max(0, izquierda);
  derecha = Math.min(100, derecha);

  const periodo = `${fechaCorta(inicio)} ${inicio.getFullYear()} — ${fechaCorta(fin)} ${fin.getFullYear()}`;
  const clases = ["cal__barra", seSaleIzquierda && "cal__barra--sigue-izq", seSaleDerecha && "cal__barra--sigue-der"];

  return (
    <button
      type="button"
      className={clases.filter(Boolean).join(" ")}
      style={{ left: `${izquierda}%`, width: `${derecha - izquierda}%`, "--color": colorCultivo(siembra.cultivo.id) }}
      title={`${siembra.cultivo.nombre} · ${periodo} · ${siembra.hectareas} ha`}
      aria-label={`${siembra.cultivo.nombre}, ${periodo}. Edit`}
      onClick={onEditar}
    >
      <Lapiz size={12} />
      <span className="cal__barra-nombre">{siembra.cultivo.nombre}</span>
      <span className="cal__barra-fechas">
        {fechaCorta(inicio)} — {fechaCorta(fin)}
      </span>
    </button>
  );
}

function Parcela({ parcela, ventana, hoy, onAgregar, onEditarParcela, onEditarSiembra }) {
  return (
    <section className="parcela" aria-label={`Plot ${parcela.nombre}`}>
      <header className="parcela__encabezado">
        <div>
          <h3>{parcela.nombre}</h3>
          <p>{parcela.hectareas} ha</p>
        </div>
        <button type="button" className="enlace" onClick={onEditarParcela}>
          Edit plot
        </button>
      </header>

      <div className="cal__fila">
        <div className="cal__pista">
          <Fondo ventana={ventana} hoy={hoy} />
          {parcela.siembras.length === 0 && <p className="cal__vacio">No crops yet</p>}
          <ul className="cal__barras">
            {parcela.siembras.map((s) => (
              <li key={s.id}>
                <Barra siembra={s} ventana={ventana} onEditar={() => onEditarSiembra(s)} />
              </li>
            ))}
          </ul>
        </div>
        <button type="button" className="cal__agregar" onClick={onAgregar} aria-label={`Add crop to ${parcela.nombre}`}>
          <Mas size={16} />
          <span>Crop</span>
        </button>
      </div>
    </section>
  );
}

const UMBRAL_ARRASTRE = 4; // px que hay que mover para que cuente como arrastre y no como clic

// `onDesplazar(fraccion)`: mueve la ventana esa fracción de su ancho (positivo = hacia el futuro).
// Se puede arrastrar con el mouse o el dedo, usar la rueda lateral del trackpad (o Shift + rueda)
// y las teclas ← → (un mes; con Shift, medio calendario) o Inicio para volver a hoy.
export default function Calendario({ plan, ventana, hoy, onDesplazar, onHoy, onAgregarSiembra, onEditarSiembra, onEditarParcela }) {
  const meses = mesesDeVentana(ventana);
  const ahora = posicion(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate(), 12), ventana);

  const raiz = useRef(null);
  const arrastre = useRef(null); // { id, x, ultimoX, movido }
  const sinClic = useRef(false); // evita que soltar un arrastre encima de una barra la abra
  const [arrastrando, setArrastrando] = useState(false);
  // La rueda necesita un listener "no pasivo" (React los registra pasivos), y ese listener vive
  // fuera del render: por eso se guardan aquí los valores más recientes.
  const ultimo = useRef({});
  ultimo.current = { onDesplazar };

  // Ancho en pixeles de una pista: sirve para pasar pixeles a fracción de la ventana.
  const anchoPista = () => raiz.current?.querySelector(".cal__pista")?.clientWidth || 1;

  useEffect(() => {
    const el = raiz.current;
    function alRodar(e) {
      const lateral = Math.abs(e.deltaX) > Math.abs(e.deltaY);
      if (!lateral && !e.shiftKey) return; // la rueda normal sigue desplazando la página
      e.preventDefault();
      const px = lateral ? e.deltaX : e.deltaY;
      ultimo.current.onDesplazar(px / anchoPista());
    }
    el.addEventListener("wheel", alRodar, { passive: false });
    return () => el.removeEventListener("wheel", alRodar);
  }, []);

  function alPresionar(e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    arrastre.current = { id: e.pointerId, x: e.clientX, ultimoX: e.clientX, movido: false };
  }

  function alMover(e) {
    const a = arrastre.current;
    if (!a || a.id !== e.pointerId) return;
    if (!a.movido) {
      if (Math.abs(e.clientX - a.x) < UMBRAL_ARRASTRE) return;
      a.movido = true;
      raiz.current.setPointerCapture(e.pointerId); // seguir el arrastre aunque el cursor salga del calendario
      setArrastrando(true);
    }
    onDesplazar(-(e.clientX - a.ultimoX) / anchoPista());
    a.ultimoX = e.clientX;
  }

  function alSoltar() {
    if (arrastre.current?.movido) {
      sinClic.current = true;
      setTimeout(() => (sinClic.current = false), 0);
    }
    arrastre.current = null;
    setArrastrando(false);
  }

  function alTeclear(e) {
    if (e.target.closest("input, select, textarea")) return;
    const paso = e.shiftKey ? 0.5 : 1 / ventana.meses; // un mes, o medio calendario con Shift
    if (e.key === "ArrowLeft") onDesplazar(-paso);
    else if (e.key === "ArrowRight") onDesplazar(paso);
    else if (e.key === "Home") onHoy();
    else return;
    e.preventDefault();
  }

  return (
    <div
      ref={raiz}
      id="calendario-siembras"
      className={`cal ${arrastrando ? "cal--arrastrando" : ""}`}
      role="group"
      aria-label="Planting calendar. Use the left and right arrow keys to move through time, Home to return to today."
      tabIndex={0}
      onPointerDown={alPresionar}
      onPointerMove={alMover}
      onPointerUp={alSoltar}
      onPointerCancel={alSoltar}
      onKeyDown={alTeclear}
      onClickCapture={(e) => {
        if (sinClic.current) {
          e.stopPropagation();
          e.preventDefault();
        }
      }}
    >
      <p className="cal__ayuda">Drag the calendar or the bar above to move through time</p>

      {/* Eje de meses: usa las mismas columnas que las filas para quedar alineado con las pistas */}
      <div className="cal__fila cal__eje">
        <ol className="cal__meses">
          {meses.filter((m) => m.visible).map((m) => (
            <li key={m.clave} style={{ left: `${m.izquierda}%`, width: `${m.ancho}%` }}>
              <b>{m.etiqueta}</b>
              {m.anio && <small>{m.anio}</small>}
            </li>
          ))}
          {ahora >= 0 && ahora <= 100 && (
            <li className="cal__hoy-etiqueta" style={{ left: `${ahora}%`, width: "auto" }}>
              TODAY
            </li>
          )}
        </ol>
        <span />
      </div>

      {plan.parcelas.map((p) => (
        <Parcela
          key={p.id}
          parcela={p}
          ventana={ventana}
          hoy={hoy}
          onAgregar={() => onAgregarSiembra(p)}
          onEditarParcela={() => onEditarParcela(p)}
          onEditarSiembra={(s) => onEditarSiembra(p, s)}
        />
      ))}
    </div>
  );
}
