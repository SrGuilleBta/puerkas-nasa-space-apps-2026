import Tarjeta from "../../components/Tarjeta.jsx";
import { Calendario, Lapiz } from "../../components/Iconos.jsx";
import { hashDe } from "../../routes.js";
import { colorCultivo } from "../../utils/colores.js";
import { deISO, fechaCorta, sumarDias } from "../../utils/fechas.js";
import { mesesDeVentana, posicion, ventanaInicial } from "../../utils/ventana.js";

const MAX_PARCELAS = 3; // más filas harían crecer demasiado la tarjeta; el resto está en el Planificador

function Barra({ siembra, ventana }) {
  const inicio = deISO(siembra.fechaSiembra);
  const fin = deISO(siembra.fechaCosecha);
  let izquierda = posicion(inicio, ventana);
  let derecha = posicion(sumarDias(fin, 1), ventana);
  if (derecha <= 0 || izquierda >= 100) return null; // fuera de los 12 meses que se muestran
  izquierda = Math.max(0, izquierda);
  derecha = Math.min(100, derecha);
  return (
    <li
      className="barra"
      style={{ left: `${izquierda}%`, width: `${derecha - izquierda}%`, "--color": colorCultivo(siembra.cultivo.id) }}
      title={`${siembra.cultivo.nombre} · ${fechaCorta(inicio)} ${inicio.getFullYear()} — ${fechaCorta(fin)} ${fin.getFullYear()}`}
    >
      <Lapiz size={11} />
      <span className="barra__nombre">{siembra.cultivo.nombre}</span>
      <span className="barra__fechas">
        {fechaCorta(inicio)} — {fechaCorta(fin)}
      </span>
    </li>
  );
}

// Los próximos 12 meses del plan que se está viendo en el Planificador, una fila por parcela.
export default function PlanAnual({ plan }) {
  const hoy = new Date();
  const ventana = ventanaInicial(12, hoy);
  const meses = mesesDeVentana(ventana);
  const ahora = posicion(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate(), 12), ventana);
  const parcelas = plan?.parcelas.slice(0, MAX_PARCELAS) ?? [];
  const ocultas = (plan?.parcelas.length ?? 0) - parcelas.length;

  return (
    <Tarjeta>
      <header className="plan__encabezado">
        <div>
          <p className="tarjeta__etiqueta">Plan anual de cultivos</p>
          <h2 className="tarjeta__titulo">{plan ? plan.nombre : "Todavía no tienes un plan"}</h2>
        </div>
        <a className="boton-secundario" href={hashDe("planificador")}>
          <Calendario size={16} /> {plan ? "Plan completo" : "Crear plan"}
        </a>
      </header>

      {parcelas.length === 0 ? (
        <p className="plan__vacio">
          {plan ? "Este plan aún no tiene parcelas." : "Crea un plan en el Planificador para ver aquí tus siembras."}
        </p>
      ) : (
        <>
          <div className="plan__cal" role="img" aria-label={`Siembras de los próximos 12 meses del ${plan.nombre}`}>
            <div className="plan__fila">
              <span />
              <ol className="plan__meses">
                {meses.filter((m) => m.visible).map((m) => (
                  <li key={m.clave} style={{ left: `${m.izquierda}%`, width: `${m.ancho}%` }}>
                    {m.etiqueta}
                    {m.anio && <small>{m.anio}</small>}
                  </li>
                ))}
                {ahora >= 0 && ahora <= 100 && (
                  <li className="plan__hoy-etiqueta" style={{ left: `${ahora}%`, width: "auto" }}>
                    HOY
                  </li>
                )}
              </ol>
            </div>

            {parcelas.map((p) => (
              <div className="plan__fila" key={p.id}>
                <span className="plan__parcela" title={`${p.nombre} · ${p.hectareas} ha`}>
                  {p.nombre}
                </span>
                <div className="plan__pista">
                  {meses.filter((m) => m.izquierda > 0 && m.izquierda < 100).map((m) => (
                    <span key={m.clave} className="plan__linea" style={{ left: `${m.izquierda}%` }} />
                  ))}
                  {ahora >= 0 && ahora <= 100 && <span className="plan__hoy" style={{ left: `${ahora}%` }} />}
                  <ul className="plan__barras">
                    {p.siembras.map((s) => (
                      <Barra key={s.id} siembra={s} ventana={ventana} />
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>

          {ocultas > 0 && (
            <a className="enlace plan__mas" href={hashDe("planificador")}>
              + {ocultas} {ocultas === 1 ? "parcela más" : "parcelas más"} en el Planificador
            </a>
          )}
        </>
      )}
    </Tarjeta>
  );
}
