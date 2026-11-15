import { useState } from "react";
import { borrarPlan, crearPlan, duplicarPlan, renombrarPlan } from "../../api/planificador.js";
import Dialogo from "../../components/Dialogo.jsx";

// `plan` es null para crear uno nuevo; si viene, se renombra o se elimina.
// onGuardado recibe { plan, borrado } para que la pantalla sepa qué plan mostrar.
function Formulario({ plan, onGuardado, onCerrar }) {
  const editando = Boolean(plan);
  const [nombre, setNombre] = useState(plan?.nombre ?? "");
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);
  // Copiar el plan a otro año: mismas parcelas y siembras con las fechas movidas
  const [nombreCopia, setNombreCopia] = useState(plan ? `${plan.nombre} (copy)` : "");
  const [anios, setAnios] = useState("1");

  async function ejecutar(accion) {
    setGuardando(true);
    setError(null);
    try {
      onGuardado(await accion());
    } catch (err) {
      setError(err);
      setConfirmaBorrar(false);
    } finally {
      setGuardando(false);
    }
  }

  function guardar(e) {
    e.preventDefault();
    if (!nombre.trim()) return setError(new Error("Enter the plan name."));
    ejecutar(async () => ({
      plan: editando ? await renombrarPlan(plan.id, nombre.trim()) : await crearPlan(nombre.trim()),
      borrado: false,
    }));
  }

  return (
    <form className="formulario" onSubmit={guardar} noValidate>
      <label className="campo">
        Plan name
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="e.g. 2027 Plan" autoFocus maxLength={80} />
      </label>

      {editando && (
        <fieldset className="economia-form">
          <legend>Copy to another year</legend>
          <p className="campo__ayuda">
            Creates a new plan with the same plots and plantings (and their yield, price and cost) with the dates moved
            forward. The original stays as it is.
          </p>
          <div className="campos">
            <label className="campo">
              Name of the copy
              <input value={nombreCopia} onChange={(e) => setNombreCopia(e.target.value)} maxLength={80} />
            </label>
            <label className="campo">
              Move dates by
              <select value={anios} onChange={(e) => setAnios(e.target.value)}>
                <option value="0">0 years (exact copy)</option>
                <option value="1">1 year</option>
                <option value="2">2 years</option>
                <option value="3">3 years</option>
              </select>
            </label>
          </div>
          <button
            type="button"
            className="btn"
            disabled={guardando || !nombreCopia.trim()}
            onClick={() =>
              ejecutar(async () => ({
                plan: await duplicarPlan(plan.id, { nombre: nombreCopia.trim(), anios: Number(anios) }),
                borrado: false,
              }))
            }
          >
            Create copy
          </button>
        </fieldset>
      )}

      {error && (
        <div className="aviso aviso--error" role="alert">
          {error.message}
        </div>
      )}

      <div className="acciones">
        {editando &&
          (confirmaBorrar ? (
            <>
              <span className="campo__ayuda">Its plots and crops will be deleted. Delete?</span>
              <button
                type="button"
                className="btn btn--peligro"
                disabled={guardando}
                onClick={() => ejecutar(async () => (await borrarPlan(plan.id), { plan, borrado: true }))}
              >
                Yes, delete
              </button>
              <button type="button" className="btn" onClick={() => setConfirmaBorrar(false)}>
                No
              </button>
            </>
          ) : (
            <button type="button" className="btn btn--peligro" onClick={() => setConfirmaBorrar(true)}>
              Delete plan
            </button>
          ))}
        <span className="acciones__espacio" />
        <button type="button" className="btn" onClick={onCerrar}>
          Cancel
        </button>
        <button type="submit" className="btn btn--primario" disabled={guardando}>
          {guardando ? "Saving…" : editando ? "Save name" : "Create plan"}
        </button>
      </div>
    </form>
  );
}

export default function DialogoPlan({ abierto, plan, onCerrar, onGuardado }) {
  return (
    <Dialogo abierto={abierto} titulo={plan ? "Edit plan" : "New plan"} onCerrar={onCerrar}>
      <Formulario plan={plan} onGuardado={onGuardado} onCerrar={onCerrar} />
    </Dialogo>
  );
}
