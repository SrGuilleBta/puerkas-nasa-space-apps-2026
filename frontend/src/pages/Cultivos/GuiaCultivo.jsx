import { useEffect, useState } from "react";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { miles, textoMeses } from "../../utils/cultivos.js";

const MODALIDAD = { irrigated: "Irrigated", rainfed: "Rainfed" };
const CICLO = { OI: "Fall–Winter", PV: "Spring–Summer", PER: "Perennial" };

const dinero = (n) => (n == null ? null : `$${miles(n)}`);

// Una fila "Título / texto" que no aparece si no hay contenido. `lista` (opcional) es la lista de
// píldoras: si viene vacía, la fila se oculta.
function Fila({ titulo, lista, children }) {
  if (lista ? lista.length === 0 : !children) return null;
  return (
    <div className="enc__guia-fila">
      <dt>{titulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Lista({ items }) {
  if (!items?.length) return null;
  return (
    <ul className="enc__pildoras">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  );
}

function Costos({ costos }) {
  const con = (costos ?? []).filter((c) => c.costo_total_ha != null || c.ingreso_neto != null);
  if (con.length === 0) return null;
  return (
    <div className="enc__tabla-caja">
      <table className="enc__tabla">
        <thead>
          <tr>
            <th scope="col">Scenario</th>
            <th scope="col">Cost per ha</th>
            <th scope="col">Net income per ha</th>
            <th scope="col">Benefit–cost</th>
          </tr>
        </thead>
        <tbody>
          {con.map((c, i) => (
            <tr key={i}>
              <th scope="row">{MODALIDAD[c.modalidad] ?? "—"}</th>
              <td>{dinero(c.costo_total_ha) ?? "—"}</td>
              <td>{dinero(c.ingreso_neto) ?? "—"}</td>
              <td>{c.relacion_bc ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <small>Pesos (MXN). Source: Agrocostos FIRA, quoted in the INIFAP agenda.</small>
    </div>
  );
}

// Guía de cultivo: consejos, detalle técnico de la agenda INIFAP del estado y rotación.
export default function GuiaCultivo({ datos: d, zona }) {
  const { ficha, manejo, indicadores: ind } = d;
  const fichas = manejo.fichas ?? [];
  const [indice, setIndice] = useState(0);
  // Al cambiar de cultivo o de zona se vuelve a la primera ficha
  useEffect(() => setIndice(0), [ficha.id, d.ubicacion.clave]);
  const f = fichas[Math.min(indice, fichas.length - 1)];

  const consejos = f?.cuidados?.length ? f.cuidados : ficha.cuidados;
  const socios = (ind?.rotacion?.socios ?? []).slice(0, 4);

  if (!consejos?.length && !f && socios.length === 0) {
    return (
      <Tarjeta>
        <EncabezadoTarjeta etiqueta="Growing guide" titulo="How to grow it" />
        <p className="enc__nada">There is no growing guide for this crop yet.</p>
      </Tarjeta>
    );
  }

  return (
    <Tarjeta className="enc__guia">
      <EncabezadoTarjeta
        etiqueta="Growing guide"
        titulo={`How to grow it${d.ubicacion.nivel === "national" ? "" : ` in ${zona}`}`}
      />

      {manejo.nota && <p className="aviso aviso--info">{manejo.nota}</p>}

      {fichas.length > 1 && (
        <div className="enc__pestanas" role="tablist" aria-label="Growing system">
          {fichas.map((x, i) => (
            <button key={x.ficha + i} type="button" role="tab" aria-selected={i === indice} onClick={() => setIndice(i)}>
              {x.modalidad ? MODALIDAD[x.modalidad] : x.ficha}
              {x.modalidad && fichas.filter((y) => y.modalidad === x.modalidad).length > 1 && ` · ${x.ficha}`}
            </button>
          ))}
        </div>
      )}

      {consejos?.length > 0 && (
        <section aria-labelledby="enc-consejos">
          <h2 id="enc-consejos" className="enc__subtitulo">
            Care tips
          </h2>
          <ol className="enc__consejos">
            {consejos.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ol>
          {!f && <p className="enc__fuente">General guidance (draft). There is no INIFAP agenda for this crop in this state.</p>}
        </section>
      )}

      {f && (
        <section aria-labelledby="enc-detalle">
          <h2 id="enc-detalle" className="enc__subtitulo">
            Technical details
          </h2>
          <dl className="enc__guia-lista">
            <Fila titulo="Planting window">
              {f.siembra?.texto}
              {f.siembra?.meses?.length > 0 && <span className="enc__meses"> ({textoMeses(f.siembra.meses)})</span>}
            </Fila>
            <Fila titulo="Area conditions">{f.region}</Fila>
            <Fila titulo="Varieties" lista={f.variedades ?? []}>
              <Lista items={f.variedades} />
            </Fila>
            <Fila titulo="Commercial hybrids" lista={f.hibridos_comerciales ?? []}>
              <Lista items={f.hibridos_comerciales} />
            </Fila>
            <Fila titulo="Seeding rate">{f.densidad}</Fila>
            <Fila titulo="Fertilization">{f.fertilizacion}</Fila>
            <Fila titulo="Irrigation">{f.riego}</Fila>
            <Fila titulo="Main pests" lista={f.plagas ?? []}>
              <Lista items={f.plagas} />
            </Fila>
            <Fila titulo="Main diseases" lista={f.enfermedades ?? []}>
              <Lista items={f.enfermedades} />
            </Fila>
            <Fila titulo="Weed management">{f.malezas}</Fila>
            <Fila titulo="Harvest">{f.cosecha}</Fila>
          </dl>
          <Costos costos={f.costos} />
          <p className="enc__fuente">
            Source: {f.cita}
            {f.revisado === false && " Summary not yet reviewed by a specialist."}
          </p>
        </section>
      )}

      {socios.length > 0 && (
        <section aria-labelledby="enc-rotacion">
          <h2 id="enc-rotacion" className="enc__subtitulo">
            Rotation ideas
          </h2>
          <ul className="enc__rotacion">
            {socios.map((s) => (
              <li key={s.socio_id}>
                <div className="enc__rotacion-cabeza">
                  <strong>{s.socio}</strong>
                  <span>{CICLO[s.ciclo_socio] ?? s.ciclo_socio}</span>
                </div>
                <div className="progreso" role="img" aria-label={`Fit ${Math.round(s.afinidad * 100)}%`}>
                  <i style={{ width: `${Math.round(s.afinidad * 100)}%` }} />
                </div>
                <small>{s.razones.slice(1).join(" · ") || s.razones[0]}</small>
              </li>
            ))}
          </ul>
          <p className="enc__fuente">
            Based on what is planted in the opposite cycle of the same {ind.rotacion.nivel_datos === "municipality" ? "municipality" : "state"} and on
            plant family and nitrogen fixation.
          </p>
        </section>
      )}
    </Tarjeta>
  );
}
