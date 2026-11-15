import { deISO, diasEntre, fechaConAnio } from "../../utils/fechas.js";

// Pestaña informativa de una siembra: estado, avance del ciclo y contexto dentro de su parcela.
export default function InfoSiembra({ parcela, siembra, hoy }) {
  const inicio = deISO(siembra.fechaSiembra);
  const fin = deISO(siembra.fechaCosecha);
  const total = Math.max(1, diasEntre(inicio, fin));
  const transcurridos = diasEntre(inicio, hoy);

  let estado, detalle, avance;
  if (hoy < inicio) {
    const faltan = diasEntre(hoy, inicio);
    estado = "Programada";
    detalle = `Se siembra en ${faltan} ${faltan === 1 ? "día" : "días"}`;
    avance = 0;
  } else if (hoy > fin) {
    estado = "Cosechada";
    detalle = `Terminó hace ${diasEntre(fin, hoy)} días`;
    avance = 100;
  } else {
    const faltan = diasEntre(hoy, fin);
    estado = "En curso";
    detalle = `Día ${transcurridos + 1} de ${total + 1} · faltan ${faltan} ${faltan === 1 ? "día" : "días"} para cosechar`;
    avance = Math.round((transcurridos / total) * 100);
  }

  // Siembras vecinas en la misma parcela (ya vienen en el plan, sin consultar nada más)
  const ordenadas = [...parcela.siembras].sort((a, b) => a.fechaSiembra.localeCompare(b.fechaSiembra));
  const i = ordenadas.findIndex((s) => s.id === siembra.id);
  const anterior = ordenadas[i - 1];
  const siguiente = ordenadas[i + 1];
  const ocupa = Math.round((siembra.hectareas / parcela.hectareas) * 100);

  return (
    <div className="info-siembra">
      <div className="info-siembra__estado">
        <span className={`info-siembra__sello info-siembra__sello--${estado === "En curso" ? "curso" : "otro"}`}>{estado}</span>
        <p>{detalle}</p>
      </div>

      <div className="info-siembra__avance" role="progressbar" aria-valuenow={avance} aria-valuemin={0} aria-valuemax={100} aria-label="Avance del ciclo">
        <span style={{ width: `${avance}%` }} />
      </div>
      <p className="campo__ayuda">Avance del ciclo: {avance}%</p>

      <dl className="info-siembra__datos">
        <div>
          <dt>Cultivo</dt>
          <dd>
            {siembra.cultivo.nombre}
            <small>
              {siembra.cultivo.tipo} · ciclo de {siembra.cultivo.cicloDias} días
            </small>
          </dd>
        </div>
        <div>
          <dt>Parcela</dt>
          <dd>
            {parcela.nombre}
            <small>
              {siembra.hectareas} de {parcela.hectareas} ha ({ocupa}%)
            </small>
          </dd>
        </div>
        <div>
          <dt>Siembra</dt>
          <dd>{fechaConAnio(inicio)}</dd>
        </div>
        <div>
          <dt>Cosecha</dt>
          <dd>
            {fechaConAnio(fin)}
            <small>{total} días de duración</small>
          </dd>
        </div>
      </dl>

      <div className="info-siembra__vecinas">
        <p>
          <b>Antes:</b> {anterior ? `${anterior.cultivo.nombre} (${anterior.cultivo.tipo})` : "nada registrado"}
        </p>
        <p>
          <b>Después:</b> {siguiente ? `${siguiente.cultivo.nombre} (${siguiente.cultivo.tipo})` : "nada programado todavía"}
        </p>
      </div>
    </div>
  );
}
