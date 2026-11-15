import Tarjeta from "../../components/Tarjeta.jsx";
import { Calendario, Lapiz } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { fechaCorta, mesCorto, porcentajeDelAnio } from "../../utils/fechas.js";

const ESTACIONES = [
  ["Primavera", "var(--primavera)"],
  ["Verano", "var(--verano)"],
  ["Otoño", "var(--otono)"],
  ["Invierno", "var(--invierno)"],
];

export default function PlanAnual({ plan }) {
  const hoy = new Date();
  const anio = hoy.getFullYear();
  const aFecha = ([mes, dia]) => new Date(anio, mes, dia);

  return (
    <Tarjeta>
      <header className="plan__encabezado">
        <div>
          <p className="tarjeta__etiqueta">Plan anual de cultivos</p>
          <h2 className="tarjeta__titulo">
            {plan.nombre} · {anio}
          </h2>
        </div>
        <a className="boton-secundario" href={hashDe("planificador")}>
          <Calendario size={16} /> Plan completo
        </a>
      </header>

      <ul className="leyenda">
        {ESTACIONES.map(([nombre, color]) => (
          <li key={nombre}>
            <i style={{ background: color }} /> {nombre}
          </li>
        ))}
      </ul>

      <div className="lineatiempo" role="img" aria-label={`Plan de siembras ${anio}`}>
        <ol className="lineatiempo__meses">
          {Array.from({ length: 12 }, (_, m) => (
            <li key={m}>{mesCorto(m).toUpperCase()}</li>
          ))}
        </ol>

        <ul className="lineatiempo__pista">
          {plan.siembras.map((s) => {
            const inicio = aFecha(s.inicio);
            const fin = aFecha(s.fin);
            const izquierda = porcentajeDelAnio(inicio);
            const ancho = porcentajeDelAnio(fin) - izquierda;
            return (
              <li
                key={s.nombre}
                className="barra"
                style={{ left: `${izquierda}%`, width: `${ancho}%`, "--color": s.color }}
              >
                <Lapiz size={12} />
                <span className="barra__nombre">{s.nombre}</span>
                <span className="barra__fechas">
                  {fechaCorta(inicio)} — {fechaCorta(fin)}
                </span>
              </li>
            );
          })}
          <li className="hoy-marca" style={{ left: `${porcentajeDelAnio(hoy)}%` }}>
            <b>HOY</b>
          </li>
        </ul>
      </div>
    </Tarjeta>
  );
}
