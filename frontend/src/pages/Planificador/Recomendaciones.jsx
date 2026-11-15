import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { Brote, Mas } from "../../components/Iconos.jsx";
import { deISO, fechaConAnio } from "../../utils/fechas.js";

// Qué sembrar después en cada parcela, con una regla simple de rotación por tipo de cultivo.
// No lleva porcentaje de "afinidad": se muestra la razón de la regla, que es lo que se sabe.
export default function Recomendaciones({ recomendaciones, onAnadir }) {
  return (
    <Tarjeta>
      <EncabezadoTarjeta etiqueta="Recommendation" titulo="What to plant next" />

      {recomendaciones.length === 0 ? (
        <p className="recomendaciones__vacio">
          Once your plots have a cereal or a legume, we will suggest here what to plant next to
          rotate your crops.
        </p>
      ) : (
        <ul className="recomendaciones">
          {recomendaciones.map((r) => (
            <li key={r.parcela.id} className="recomendacion">
              <span className="recomendacion__icono">
                <Brote size={20} />
              </span>
              <div className="recomendacion__texto">
                <p className="recomendacion__contexto">
                  <b>{r.parcela.nombre}</b> · after {r.despuesDe.cultivo.nombre} (harvest{" "}
                  {fechaConAnio(deISO(r.despuesDe.fechaCosecha))})
                </p>
                <p className="recomendacion__sugerencia">
                  Consider <b>{r.sugerido.nombre}</b> from {fechaConAnio(deISO(r.desde))}
                </p>
                <p className="recomendacion__razon">{r.razon}</p>
              </div>
              <button type="button" className="btn recomendacion__boton" onClick={() => onAnadir(r)}>
                <Mas size={14} /> Add to plan
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="recomendaciones__nota">Rotation rule: after a cereal, a legume; after a legume, a cereal.</p>
    </Tarjeta>
  );
}
