import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { Brote, Flecha, Mas, Menos, Tendencia } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { fechaLarga } from "../../utils/fechas.js";

const pesos = new Intl.NumberFormat("es-MX");

export default function CultivoActivo({ cultivo }) {
  const avance = Math.min(100, Math.round((cultivo.dia / cultivo.cicloDias) * 100));

  return (
    <Tarjeta>
      <EncabezadoTarjeta
        etiqueta="Cultivos activos"
        titulo="Tu cosecha"
        derecha={
          <a className="enlace" href={hashDe("cultivos")}>
            Ver todos
          </a>
        }
      />

      <div className="cultivo__imagen">
        <span className="cultivo__brote">
          <Brote size={30} />
        </span>
        <span className="cultivo__etapa">
          ETAPA {cultivo.etapa} DE {cultivo.etapas}
        </span>
      </div>

      <div className="cultivo__fila">
        <div>
          <h3 className="cultivo__nombre">{cultivo.nombre}</h3>
          <p className="cultivo__meta">
            {cultivo.hectareas} ha · Día {cultivo.dia}
          </p>
        </div>
        <span className="cultivo__variacion">
          <Tendencia size={14} />+{cultivo.variacion}%
        </span>
      </div>

      <div className="cultivo__fila cultivo__fila--precio">
        <span>Precio actual</span>
        <strong>
          ${pesos.format(cultivo.precio)} <small>MXN/t</small>
        </strong>
      </div>

      <div
        className="progreso"
        role="progressbar"
        aria-label="Avance del ciclo"
        aria-valuenow={avance}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <i style={{ width: `${avance}%` }} />
      </div>

      <div className="cultivo__fila cultivo__fila--cosecha">
        <span>Cosecha estimada</span>
        <strong>{fechaLarga(cultivo.cosecha)}</strong>
      </div>

      <div className="cultivo__chips">
        {cultivo.chips.map((c) => (
          <div key={c.titulo} className={`chip chip--${c.tipo}`}>
            <span className="chip__icono">{c.tipo === "positivo" ? <Mas size={14} /> : <Menos size={14} />}</span>
            <span>
              <strong>{c.titulo}</strong>
              <small>{c.detalle}</small>
            </span>
          </div>
        ))}
      </div>

      <a className="boton-principal" href={hashDe("planificador")}>
        Ver plan del cultivo <Flecha size={16} />
      </a>
    </Tarjeta>
  );
}
