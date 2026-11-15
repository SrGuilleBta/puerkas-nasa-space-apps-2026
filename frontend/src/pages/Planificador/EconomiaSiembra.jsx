import { numero, pesos } from "../../utils/formato.js";

// Costos e ingresos estimados de una siembra, con los datos que capturó la persona (se editan en "Edit").
// Cada cifra solo aparece si hay datos para calcularla.
export default function EconomiaSiembra({ siembra }) {
  const { rendimientoTHa: rend, precioT: precio, costoHa: costo } = siembra;
  const hayDatos = rend != null || precio != null || costo != null;
  if (!hayDatos) {
    return (
      <p className="campo__ayuda">
        Add the expected yield, price and cost in the Edit tab to see the estimated income and profit.
      </p>
    );
  }
  return (
    <section className="economia" aria-label="Estimated economics">
      <h3>Estimated economics</h3>
      <dl className="info-siembra__nasa-datos">
        {siembra.ingresoEstimado != null && (
          <div>
            <dt>Income</dt>
            <dd>{pesos(siembra.ingresoEstimado)}</dd>
          </div>
        )}
        {siembra.costoTotal != null && (
          <div>
            <dt>Cost</dt>
            <dd>{pesos(siembra.costoTotal)}</dd>
          </div>
        )}
        {siembra.gananciaEstimada != null && (
          <div>
            <dt>Profit</dt>
            <dd className={siembra.gananciaEstimada < 0 ? "economia__perdida" : "economia__ganancia"}>
              {pesos(siembra.gananciaEstimada)}
            </dd>
          </div>
        )}
      </dl>
      <small>
        Based on {siembra.hectareas} ha
        {rend != null && ` · ${numero(rend)} t/ha`}
        {precio != null && ` · ${pesos(precio)}/t`}
        {costo != null && ` · ${pesos(costo)}/ha`}. Estimates, not a forecast.
        {(rend == null || precio == null) && siembra.ingresoEstimado == null && " Add yield and price to see the income."}
        {costo == null && siembra.costoTotal == null && " Add the cost per hectare to see the cost and profit."}
      </small>
    </section>
  );
}
