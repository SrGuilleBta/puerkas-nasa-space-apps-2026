import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { Brote, Mas } from "../../components/Iconos.jsx";
import { deISO, fechaConAnio } from "../../utils/fechas.js";

// Qué sembrar después en cada parcela, con una regla simple de rotación por tipo de cultivo.
// No lleva porcentaje de "afinidad": se muestra la razón de la regla, que es lo que se sabe.
export default function Recomendaciones({ recomendaciones, onAnadir }) {
  return (
    <Tarjeta>
      <EncabezadoTarjeta etiqueta="Recomendación" titulo="Qué sembrar después" />

      {recomendaciones.length === 0 ? (
        <p className="recomendaciones__vacio">
          Cuando tus parcelas tengan un cereal o una leguminosa, aquí te sugeriremos qué sembrar después para
          rotar el cultivo.
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
                  <b>{r.parcela.nombre}</b> · después de {r.despuesDe.cultivo.nombre} (cosecha{" "}
                  {fechaConAnio(deISO(r.despuesDe.fechaCosecha))})
                </p>
                <p className="recomendacion__sugerencia">
                  Considera <b>{r.sugerido.nombre}</b> desde el {fechaConAnio(deISO(r.desde))}
                </p>
                <p className="recomendacion__razon">{r.razon}</p>
              </div>
              <button type="button" className="btn recomendacion__boton" onClick={() => onAnadir(r)}>
                <Mas size={14} /> Añadir al plan
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="recomendaciones__nota">Regla de rotación: después de un cereal, una leguminosa; después de una leguminosa, un cereal.</p>
    </Tarjeta>
  );
}
