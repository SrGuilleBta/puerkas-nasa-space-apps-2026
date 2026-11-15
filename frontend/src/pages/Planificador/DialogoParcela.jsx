import { useState } from "react";
import { borrarParcela, crearParcela, editarParcela } from "../../api/planificador.js";
import Dialogo from "../../components/Dialogo.jsx";

function Formulario({ planId, parcela, onGuardado, onCerrar }) {
  const editando = Boolean(parcela);
  const [nombre, setNombre] = useState(parcela?.nombre ?? "");
  const [hectareas, setHectareas] = useState(String(parcela?.hectareas ?? ""));
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);

  async function ejecutar(accion) {
    setGuardando(true);
    setError(null);
    try {
      await accion();
      onGuardado();
    } catch (err) {
      setError(err);
      setConfirmaBorrar(false);
    } finally {
      setGuardando(false);
    }
  }

  function guardar(e) {
    e.preventDefault();
    if (!nombre.trim()) return setError(new Error("Enter the plot name."));
    if (!(Number(hectareas) > 0)) return setError(new Error("Hectares must be greater than 0."));
    const datos = { nombre: nombre.trim(), hectareas: Number(hectareas) };
    ejecutar(() => (editando ? editarParcela(parcela.id, datos) : crearParcela(planId, datos)));
  }

  const siembras = parcela?.siembras.length ?? 0;

  return (
    <form className="formulario" onSubmit={guardar} noValidate>
      <label className="campo">
        Name
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="e.g. North Field" autoFocus maxLength={80} />
      </label>
      <label className="campo">
        Hectares
        <input type="number" step="0.1" min="0.1" value={hectareas} onChange={(e) => setHectareas(e.target.value)} />
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
              <span className="campo__ayuda">
                {siembras ? `Its ${siembras} ${siembras === 1 ? "crop" : "crops"} will be deleted too. ` : ""}Delete?
              </span>
              <button type="button" className="btn btn--peligro" disabled={guardando} onClick={() => ejecutar(() => borrarParcela(parcela.id))}>
                Yes, delete
              </button>
              <button type="button" className="btn" onClick={() => setConfirmaBorrar(false)}>
                No
              </button>
            </>
          ) : (
            <button type="button" className="btn btn--peligro" onClick={() => setConfirmaBorrar(true)}>
              Delete
            </button>
          ))}
        <span className="acciones__espacio" />
        <button type="button" className="btn" onClick={onCerrar}>
          Cancel
        </button>
        <button type="submit" className="btn btn--primario" disabled={guardando}>
          {guardando ? "Saving…" : editando ? "Save changes" : "Add plot"}
        </button>
      </div>
    </form>
  );
}

export default function DialogoParcela({ abierto, planId, parcela, onCerrar, onGuardado }) {
  return (
    <Dialogo abierto={abierto} titulo={parcela ? "Edit plot" : "Add plot"} onCerrar={onCerrar}>
      <Formulario planId={planId} parcela={parcela} onGuardado={onGuardado} onCerrar={onCerrar} />
    </Dialogo>
  );
}
