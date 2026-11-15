import { getVentanaSiembra } from "../../api/planificador.js";
import { getEstado } from "../../api/suelo.js";
import useDatos from "../../hooks/useDatos.js";
import { deISO, diasEntre } from "../../utils/fechas.js";
import { resumenAgua } from "../Suelo/resumen.js";

// La humedad medida por SMAP describe los últimos 30 días: solo dice algo de una siembra que es pronto
const DIAS_ANTES = 7;
const DIAS_DESPUES = 30;

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
// `fechaInicio` (AAAA-MM-DD) es la fecha de siembra: si es de aquí a un mes, también se avisa si el suelo
// está más seco de lo normal ahora (módulo Suelo, SMAP).
// No aparece si el cultivo es perenne, si no viene del catálogo o si falla la consulta.
export default function VentanaSiembra({ catalogoId, municipio, mesInicio, fechaInicio }) {
  const v = useDatos(() => getVentanaSiembra(catalogoId, municipio), [catalogoId, municipio]).datos;

  const faltan = fechaInicio ? diasEntre(new Date(), deISO(fechaInicio)) : null;
  const pronto = faltan !== null && faltan >= -DIAS_ANTES && faltan <= DIAS_DESPUES;
  const suelo = useDatos(() => (pronto ? getEstado({ municipio }) : Promise.resolve(null)), [municipio, pronto]);
  const agua = pronto && !suelo.error ? resumenAgua(suelo.datos) : null;

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
      {agua && agua.tono !== "bien" && (
        <p className="aviso aviso--info">
          <b>Soil moisture right now: {agua.titulo.toLowerCase()}.</b> {agua.frase}. If you plant soon, plan on irrigation
          or wait for rain.
        </p>
      )}
      <small>
        Based on NASA POWER monthly averages and the crop's ideal temperature (EcoCrop)
        {pronto ? ", and NASA SMAP soil moisture of the last 30 days" : ""}. Local varieties and practices vary: confirm
        with a technician.
      </small>
    </section>
  );
}
