import { useRef, useState } from "react";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { Brote, Flecha } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { colorCultivo } from "../../utils/colores.js";
import { deISO, fechaLarga } from "../../utils/fechas.js";
import { numero, pesos } from "../../utils/formato.js";

// "4 de enero" y, si no es de este año, "4 de enero de 2027".
function fechaCosecha(texto) {
  const f = deISO(texto);
  return f.getFullYear() === new Date().getFullYear() ? fechaLarga(f) : `${fechaLarga(f)}, ${f.getFullYear()}`;
}

// Precio y rendimiento de SIAP para el estado de la ubicación (o del país), y chips de rentabilidad
// y sequía. La flecha compara el precio del último año con su mediana de 10 años.
function Mercado({ m }) {
  const porUnidad = (m.precioUnidad ?? "").replace(/^\$/, ""); // "$/t" -> "/t"
  const v = m.variacionPct;
  return (
    <div className="cultivo__mercado">
      <dl>
        {m.precio != null && (
          <div>
            <dt>Price{m.anio ? ` ${m.anio}` : ""}</dt>
            <dd>
              {pesos(m.precio)}
              {porUnidad}
              {v != null && Math.abs(v) >= 1 && (
                <small
                  className={v > 0 ? "tendencia tendencia--sube" : "tendencia tendencia--baja"}
                  title="Latest yearly farm-gate price compared with its 10-year median (inflation-adjusted)"
                >
                  {v > 0 ? "▲" : "▼"} {Math.abs(v)}%
                </small>
              )}
            </dd>
          </div>
        )}
        {m.rendimiento != null && (
          <div>
            <dt>Typical yield</dt>
            <dd>
              {numero(m.rendimiento)} {m.rendimientoUnidad}
            </dd>
          </div>
        )}
      </dl>
      {m.etiquetas.length > 0 && (
        <ul className="cultivo__chips">
          {m.etiquetas.map((e) => (
            <li key={e.texto} className={`chip chip--${e.tipo}`}>
              {e.texto}
            </li>
          ))}
        </ul>
      )}
      <small className="cultivo__fuente">Source: {m.fuente}</small>
    </div>
  );
}

function Siembra({ s }) {
  return (
    <>
      <div className="cultivo__imagen" style={{ "--color": colorCultivo(s.cultivo.id) }}>
        <span className="cultivo__brote">
          <Brote size={30} />
        </span>
        <span className="cultivo__etapa">
          STAGE {s.etapa} OF {s.etapas}
        </span>
      </div>

      <div>
        <h3 className="cultivo__nombre">{s.cultivo.nombre}</h3>
        <p className="cultivo__meta">
          {s.hectareas} ha · {s.parcela.nombre} · Day {s.dia}
        </p>
      </div>

      {s.mercado && <Mercado m={s.mercado} />}

      <div>
        <div className="cultivo__fila cultivo__fila--precio">
          <span>Cycle progress</span>
          <strong>{s.avance}%</strong>
        </div>
        <div className="progreso" role="progressbar" aria-label="Cycle progress" aria-valuenow={s.avance} aria-valuemin={0} aria-valuemax={100}>
          <i style={{ width: `${s.avance}%` }} />
        </div>
        <div className="cultivo__fila cultivo__fila--cosecha">
          <span>Estimated harvest</span>
          <strong>{fechaCosecha(s.fechaCosecha)}</strong>
        </div>
      </div>
    </>
  );
}

// Carrusel: cada cultivo en curso hoy es una diapositiva. Se desliza con el dedo (scroll-snap),
// con las flechas, con los puntos o con las teclas ← →.
export default function CultivosActivos({ activos }) {
  const pista = useRef(null);
  const [indice, setIndice] = useState(0);
  const varios = activos.length > 1;

  function ir(i) {
    const el = pista.current;
    const sinAnimar = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({ left: i * el.clientWidth, behavior: sinAnimar ? "auto" : "smooth" });
  }

  const alDesplazar = () => {
    const el = pista.current;
    setIndice(Math.min(activos.length - 1, Math.round(el.scrollLeft / el.clientWidth)));
  };

  function alTeclear(e) {
    if (e.key === "ArrowRight" && indice < activos.length - 1) ir(indice + 1);
    if (e.key === "ArrowLeft" && indice > 0) ir(indice - 1);
  }

  return (
    <Tarjeta className="cultivos">
      <EncabezadoTarjeta
        etiqueta="Active crops"
        titulo="Your harvest"
        derecha={
          <a className="enlace" href={hashDe("planificador")}>
            View all
          </a>
        }
      />

      {activos.length === 0 ? (
        <div className="cultivos__vacio">
          <span className="cultivo__brote">
            <Brote size={30} />
          </span>
          <p>No crops are growing today.</p>
          <a className="boton-secundario" href={hashDe("planificador")}>
            Plan a crop
          </a>
        </div>
      ) : (
        <>
          <div
            className="carrusel"
            role="region"
            aria-roledescription="carousel"
            aria-label="Crops in progress"
            tabIndex={varios ? 0 : undefined}
            onKeyDown={alTeclear}
          >
            <div className="carrusel__pista" ref={pista} onScroll={alDesplazar}>
              {activos.map((s, i) => (
                <div
                  key={s.id}
                  className="carrusel__diapositiva"
                  role="group"
                  aria-roledescription="slide"
                  aria-label={`${i + 1} of ${activos.length}`}
                  // Las diapositivas fuera de vista no reciben foco ni se leen
                  inert={i === indice ? undefined : ""}
                >
                  <Siembra s={s} />
                </div>
              ))}
            </div>

            {varios && (
              <div className="carrusel__controles">
                <button type="button" className="carrusel__flecha carrusel__flecha--atras" aria-label="Previous crop" disabled={indice === 0} onClick={() => ir(indice - 1)}>
                  <Flecha size={14} />
                </button>
                <span className="carrusel__puntos">
                  {activos.map((s, i) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`carrusel__punto ${i === indice ? "carrusel__punto--activo" : ""}`}
                      aria-label={`View ${s.cultivo.nombre}, ${s.parcela.nombre}`}
                      aria-current={i === indice ? "true" : undefined}
                      onClick={() => ir(i)}
                    />
                  ))}
                </span>
                <button type="button" className="carrusel__flecha" aria-label="Next crop" disabled={indice === activos.length - 1} onClick={() => ir(indice + 1)}>
                  <Flecha size={14} />
                </button>
              </div>
            )}
          </div>

          <a className="boton-principal" href={hashDe("planificador")}>
            View crop plan <Flecha size={16} />
          </a>
        </>
      )}
    </Tarjeta>
  );
}
