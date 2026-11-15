import { getVentanaSiembra } from "../../api/planificador.js";
import useDatos from "../../hooks/useDatos.js";

const MESES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const NIVEL = { good: "Good", fair: "Fair", poor: "Poor" };

// "Mar–Jul"; con vuelta de año, "Nov–Feb". `meses` va de 1 a 12.
function rangos(meses) {
  const hay = new Set(meses);
  const tramos = [];
  for (const m of meses) {
    const anterior = m === 1 ? 12 : m - 1;
    if (hay.has(anterior) && hay.size < 12) continue; // no empieza un tramo aquí
    let fin = m;
    while (hay.has(fin === 12 ? 1 : fin + 1) && fin !== (m === 1 ? 12 : m - 1)) fin = fin === 12 ? 1 : fin + 1;
    tramos.push(fin === m ? MESES[m - 1] : `${MESES[m - 1]}–${MESES[fin - 1]}`);
  }
  return hay.size === 12 ? "any month" : tramos.join(", ");
}

// Mejor época para sembrar este cultivo en la ubicación activa (temperatura ideal del cultivo contra
// el clima promedio de NASA POWER). `mesInicio` (1-12) marca el mes elegido y avisa si no conviene.
// No aparece si el cultivo es perenne, si no viene del catálogo o si falla la consulta.
export default function VentanaSiembra({ catalogoId, municipio, mesInicio }) {
  const v = useDatos(() => getVentanaSiembra(catalogoId, municipio), [catalogoId, municipio]).datos;
  if (!v || !v.estacional) return null;

  const elegido = v.meses.find((m) => m.mes === mesInicio);
  return (
    <section className="ventana" aria-label="When to plant here">
      <h3>When to plant here</h3>
      <p className="ventana__resumen">
        {v.mejores.length > 0 ? (
          <>
            {v.nivelMejores === "good" ? "Best" : "Acceptable"}: <b>{rangos(v.mejores)}</b>
          </>
        ) : (
          "No month fits this crop's temperature range well here."
        )}
      </p>
      <ol className="ventana__meses">
        {v.meses.map((m) => (
          <li
            key={m.mes}
            className={`ventana__mes ventana__mes--${m.nivel}${m.mes === mesInicio ? " ventana__mes--elegido" : ""}`}
            title={`${MESES[m.mes - 1]}: ${NIVEL[m.nivel]} · ${m.tempMedia} °C average over the cycle · ${m.lluviaMm} mm of rain`}
          >
            {MESES[m.mes - 1]}
          </li>
        ))}
      </ol>
      {elegido && elegido.nivel !== "good" && (
        <p className="aviso aviso--info">
          {MESES[elegido.mes - 1]} is {elegido.nivel === "fair" ? "acceptable but not ideal" : "not a good month"} for this crop here:
          the average temperature over its cycle is {elegido.tempMedia} °C and it prefers {v.temperaturaIdealC[0]}–
          {v.temperaturaIdealC[1]} °C.
        </p>
      )}
      {elegido?.necesitaRiego && (
        <p className="aviso aviso--info">
          Only about {elegido.lluviaMm} mm of rain is expected over the cycle starting in {MESES[elegido.mes - 1]}, which is
          below what this crop prefers: plan on irrigation.
        </p>
      )}
      <small>
        Based on NASA POWER monthly averages and the crop's ideal temperature (EcoCrop). Local varieties and practices
        vary: confirm with a technician.
      </small>
    </section>
  );
}
