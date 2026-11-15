import { Lapiz, Mas } from "../../components/Iconos.jsx";
import { colorCultivo } from "../../utils/colores.js";
import { deISO, fechaCorta, sumarDias } from "../../utils/fechas.js";
import { estaciones, mesesDeVentana, posicion } from "../../utils/ventana.js";

// Fondo de estaciones y línea de "hoy": van dentro de la pista de cada parcela.
function Fondo({ ventana, hoy }) {
  const ahora = posicion(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate(), 12), ventana);
  return (
    <>
      {estaciones(ventana).map((e, i) => (
        <span
          key={i}
          className={`cal__estacion cal__estacion--${e.nombre}`}
          style={{ left: `${e.izquierda}%`, width: `${e.ancho}%` }}
        />
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
      aria-label={`${siembra.cultivo.nombre}, ${periodo}. Editar`}
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
    <section className="parcela" aria-label={`Parcela ${parcela.nombre}`}>
      <header className="parcela__encabezado">
        <div>
          <h3>{parcela.nombre}</h3>
          <p>{parcela.hectareas} ha</p>
        </div>
        <button type="button" className="enlace" onClick={onEditarParcela}>
          Editar parcela
        </button>
      </header>

      <div className="cal__fila">
        <div className="cal__pista">
          <Fondo ventana={ventana} hoy={hoy} />
          {parcela.siembras.length === 0 && <p className="cal__vacio">Aún sin cultivos</p>}
          <ul className="cal__barras">
            {parcela.siembras.map((s) => (
              <li key={s.id}>
                <Barra siembra={s} ventana={ventana} onEditar={() => onEditarSiembra(s)} />
              </li>
            ))}
          </ul>
        </div>
        <button type="button" className="cal__agregar" onClick={onAgregar} aria-label={`Añadir cultivo a ${parcela.nombre}`}>
          <Mas size={16} />
          <span>Cultivo</span>
        </button>
      </div>
    </section>
  );
}

export default function Calendario({ plan, ventana, hoy, onAgregarSiembra, onEditarSiembra, onEditarParcela }) {
  const meses = mesesDeVentana(ventana);
  const ahora = posicion(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate(), 12), ventana);

  return (
    <div className="cal">
      {/* Eje de meses: usa las mismas columnas que las filas para quedar alineado con las pistas */}
      <div className="cal__fila cal__eje">
        <ol className="cal__meses">
          {meses.map((m) => (
            <li key={m.clave} style={{ left: `${m.izquierda}%`, width: `${m.ancho}%` }}>
              <b>{m.etiqueta}</b>
              {m.anio && <small>{m.anio}</small>}
            </li>
          ))}
          {ahora >= 0 && ahora <= 100 && (
            <li className="cal__hoy-etiqueta" style={{ left: `${ahora}%`, width: "auto" }}>
              HOY
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
