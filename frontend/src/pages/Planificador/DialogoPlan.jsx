import { useState } from "react";
import { borrarPlan, crearPlan, renombrarPlan } from "../../api/planificador.js";
import Dialogo from "../../components/Dialogo.jsx";

// `plan` es null para crear uno nuevo; si viene, se renombra o se elimina.
// onGuardado recibe { plan, borrado } para que la pantalla sepa qué plan mostrar.
function Formulario({ plan, onGuardado, onCerrar }) {
  const editando = Boolean(plan);
  const [nombre, setNombre] = useState(plan?.nombre ?? "");
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);

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
    if (!nombre.trim()) return setError(new Error("Escribe el nombre del plan."));
    ejecutar(async () => ({
      plan: editando ? await renombrarPlan(plan.id, nombre.trim()) : await crearPlan(nombre.trim()),
      borrado: false,
    }));
  }

  return (
    <form className="formulario" onSubmit={guardar} noValidate>
      <label className="campo">
        Nombre del plan
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej. Plan 2027" autoFocus maxLength={80} />
      </label>

      {error && (
        <div className="aviso aviso--error" role="alert">
          {error.message}
        </div>
      )}

      <div className="acciones">
        {editando &&
          (confirmaBorrar ? (
            <>
              <span className="campo__ayuda">Se borrarán sus parcelas y cultivos. ¿Eliminar?</span>
              <button
                type="button"
                className="btn btn--peligro"
                disabled={guardando}
                onClick={() => ejecutar(async () => (await borrarPlan(plan.id), { plan, borrado: true }))}
              >
                Sí, eliminar
              </button>
              <button type="button" className="btn" onClick={() => setConfirmaBorrar(false)}>
                No
              </button>
            </>
          ) : (
            <button type="button" className="btn btn--peligro" onClick={() => setConfirmaBorrar(true)}>
              Eliminar plan
            </button>
          ))}
        <span className="acciones__espacio" />
        <button type="button" className="btn" onClick={onCerrar}>
          Cancelar
        </button>
        <button type="submit" className="btn btn--primario" disabled={guardando}>
          {guardando ? "Guardando…" : editando ? "Guardar nombre" : "Crear plan"}
        </button>
      </div>
    </form>
  );
}

export default function DialogoPlan({ abierto, plan, onCerrar, onGuardado }) {
  return (
    <Dialogo abierto={abierto} titulo={plan ? "Editar plan" : "Nuevo plan"} onCerrar={onCerrar}>
      <Formulario plan={plan} onGuardado={onGuardado} onCerrar={onCerrar} />
    </Dialogo>
  );
}
