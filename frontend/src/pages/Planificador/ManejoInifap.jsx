import { useState } from "react";
import { fijarEstado, listarEstados, listarUbicaciones } from "../../api/ubicaciones.js";
import useDatos from "../../hooks/useDatos.js";

const FILAS = [
  ["Planting", (f) => f.siembra?.texto],
  ["Varieties", (f) => f.variedades.join(", ")],
  ["Planting density", (f) => f.densidad],
  ["Fertilization", (f) => f.fertilizacion],
  ["Irrigation", (f) => f.riego],
  ["Weed control", (f) => f.malezas],
  ["Pests", (f) => f.plagas.join(", ")],
  ["Diseases", (f) => f.enfermedades.join(", ")],
  ["Harvest", (f) => f.cosecha],
];

// Para elegir el estado de la ubicación activa y poder mostrar el manejo del INIFAP de ese estado.
function ElegirEstado({ municipio, onElegido }) {
  const estados = useDatos(listarEstados, []);
  const [clave, setClave] = useState("");
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      const mia = (await listarUbicaciones()).find((u) => u.nombre === municipio);
      if (!mia) throw new Error("Could not find the active location.");
      await fijarEstado(mia.id, clave);
      onElegido();
    } catch (err) {
      setError(err);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="manejo__estado">
      <p>Choose your state to see the INIFAP technical guide for this crop.</p>
      <div className="manejo__estado-fila">
        <select value={clave} onChange={(e) => setClave(e.target.value)} aria-label="State">
          <option value="">Choose a state…</option>
          {(estados.datos ?? []).map((e) => (
            <option key={e.clave} value={e.clave}>
              {e.nombre}
            </option>
          ))}
        </select>
        <button type="button" className="btn" disabled={!clave || guardando} onClick={guardar}>
          Save state
        </button>
      </div>
      {error && <p className="aviso aviso--error">{error.message}</p>}
    </div>
  );
}

// Manejo del cultivo según las agendas técnicas del INIFAP del estado de la ubicación activa.
// El texto de las agendas viene del INIFAP tal cual (en español); las etiquetas son de la interfaz.
export default function ManejoInifap({ manejo, municipio, onEstado }) {
  const [elegida, setElegida] = useState(0);
  const [cambiando, setCambiando] = useState(false);

  if (manejo.necesitaEstado || cambiando) {
    return (
      <ElegirEstado
        municipio={municipio}
        onElegido={() => {
          setCambiando(false);
          onEstado();
        }}
      />
    );
  }
  if (manejo.fichas.length === 0) {
    return (
      <p className="campo__ayuda">
        No INIFAP technical guide for this crop in {manejo.estado}. The general care tips above apply.
      </p>
    );
  }

  const f = manejo.fichas[Math.min(elegida, manejo.fichas.length - 1)];
  return (
    <div className="manejo">
      <b>INIFAP technical guide · {manejo.estado}</b>
      {manejo.fichas.length > 1 && (
        <div className="manejo__modalidades" role="tablist" aria-label="Production system">
          {manejo.fichas.map((x, i) => (
            <button key={i} type="button" role="tab" aria-selected={i === elegida} onClick={() => setElegida(i)}>
              {["riego", "irrigated"].includes(x.modalidad) ? "Irrigated" : ["temporal", "rainfed"].includes(x.modalidad) ? "Rainfed" : `Option ${i + 1}`}
              {x.ciclo ? ` · ${x.ciclo}` : ""}
            </button>
          ))}
        </div>
      )}
      {f.region && <p className="manejo__region">{f.region}</p>}
      <dl className="manejo__datos">
        {FILAS.map(([etiqueta, valor]) => {
          const texto = valor(f);
          return texto ? (
            <div key={etiqueta}>
              <dt>{etiqueta}</dt>
              <dd>{texto}</dd>
            </div>
          ) : null;
        })}
      </dl>
      {f.cuidados.length > 0 && (
        <>
          <b>Tips from the technical guide</b>
          <ul>
            {f.cuidados.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </>
      )}
      <small>
        {f.cita}
        {!f.revisado && " Summarized automatically: confirm with a technician before acting."}{" "}
        <button type="button" className="manejo__cambiar" onClick={() => setCambiando(true)}>
          Change state
        </button>
      </small>
    </div>
  );
}
