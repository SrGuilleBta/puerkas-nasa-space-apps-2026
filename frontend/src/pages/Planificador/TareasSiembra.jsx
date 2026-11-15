import { useState } from "react";
import { borrarTarea, crearTarea, editarTarea, listarTareas, tareasSugeridas } from "../../api/planificador.js";
import useDatos from "../../hooks/useDatos.js";
import { aISO, deISO, fechaCorta } from "../../utils/fechas.js";

const TIPOS = [
  ["plant", "Planting"],
  ["weed", "Weed control"],
  ["fertilize", "Fertilize"],
  ["irrigate", "Irrigate"],
  ["pests", "Pests and disease"],
  ["harvest", "Harvest"],
  ["other", "Other"],
];
const ETIQUETA = Object.fromEntries(TIPOS);

// Tareas de una siembra (fertilizar, regar, cosechar...) con marca de hecha. Las que no están hechas y
// ya pasaron salen como vencidas. `onCambio` avisa a la pantalla para actualizar el contador del resumen.
export default function TareasSiembra({ siembra, hoy, onCambio }) {
  const tareas = useDatos(() => listarTareas(siembra.id), [siembra.id]);
  const [titulo, setTitulo] = useState("");
  const [tipo, setTipo] = useState("other");
  const [fecha, setFecha] = useState(siembra.fechaSiembra);
  const [error, setError] = useState(null);
  const [ocupado, setOcupado] = useState(false);

  async function ejecutar(accion) {
    setOcupado(true);
    setError(null);
    try {
      await accion();
      tareas.recargar();
      onCambio?.();
    } catch (err) {
      setError(err);
    } finally {
      setOcupado(false);
    }
  }

  function agregar(e) {
    e.preventDefault();
    if (!titulo.trim()) return setError(new Error("Enter a name for the task."));
    if (!fecha) return setError(new Error("Choose a date."));
    ejecutar(async () => {
      await crearTarea(siembra.id, { titulo: titulo.trim(), tipo, fecha });
      setTitulo("");
    });
  }

  const lista = tareas.datos ?? [];
  const hoyISO = aISO(hoy);
  return (
    <section className="tareas" aria-label="Tasks">
      <h3>Tasks</h3>

      {lista.length === 0 && !tareas.cargando && (
        <div className="tareas__vacio">
          <p>No tasks yet. Add your own or start from a general schedule spread over the crop cycle.</p>
          <button type="button" className="btn" disabled={ocupado} onClick={() => ejecutar(() => tareasSugeridas(siembra.id))}>
            Add suggested schedule
          </button>
        </div>
      )}

      {lista.length > 0 && (
        <ul className="tareas__lista">
          {lista.map((t) => {
            const vencida = !t.hecha && t.fecha < hoyISO;
            return (
              <li key={t.id} className={`tarea${t.hecha ? " tarea--hecha" : ""}${vencida ? " tarea--vencida" : ""}`}>
                <input
                  type="checkbox"
                  checked={t.hecha}
                  disabled={ocupado}
                  aria-label={`Mark "${t.titulo}" as ${t.hecha ? "not done" : "done"}`}
                  onChange={(e) => ejecutar(() => editarTarea(t.id, { hecha: e.target.checked }))}
                />
                <span className="tarea__texto">
                  <b>{t.titulo}</b>
                  <small>
                    {ETIQUETA[t.tipo] ?? t.tipo} · {fechaCorta(deISO(t.fecha))}
                    {vencida && " · Overdue"}
                  </small>
                </span>
                <button type="button" className="tarea__borrar" disabled={ocupado} aria-label={`Delete "${t.titulo}"`} onClick={() => ejecutar(() => borrarTarea(t.id))}>
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <form className="tareas__nueva" onSubmit={agregar} noValidate>
        <input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="New task, e.g. Apply fertilizer" maxLength={80} aria-label="Task name" />
        <select value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Task type">
          {TIPOS.map(([id, texto]) => (
            <option key={id} value={id}>
              {texto}
            </option>
          ))}
        </select>
        <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} aria-label="Task date" />
        <button type="submit" className="btn" disabled={ocupado}>
          Add
        </button>
      </form>

      {(error || tareas.error) && (
        <p className="aviso aviso--error" role="alert">
          {(error ?? tareas.error).message}
        </p>
      )}
    </section>
  );
}
