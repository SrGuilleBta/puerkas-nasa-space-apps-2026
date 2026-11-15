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
    if (!nombre.trim()) return setError(new Error("Escribe el nombre de la parcela."));
    if (!(Number(hectareas) > 0)) return setError(new Error("Las hectáreas deben ser mayores a 0."));
    const datos = { nombre: nombre.trim(), hectareas: Number(hectareas) };
    ejecutar(() => (editando ? editarParcela(parcela.id, datos) : crearParcela(planId, datos)));
  }

  const siembras = parcela?.siembras.length ?? 0;

  return (
    <form className="formulario" onSubmit={guardar} noValidate>
      <label className="campo">
        Nombre
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej. La Esperanza" autoFocus maxLength={80} />
      </label>
      <label className="campo">
        Hectáreas
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
                {siembras ? `Se borrarán también sus ${siembras} cultivos. ` : ""}¿Eliminar?
              </span>
              <button type="button" className="btn btn--peligro" disabled={guardando} onClick={() => ejecutar(() => borrarParcela(parcela.id))}>
                Sí, eliminar
              </button>
              <button type="button" className="btn" onClick={() => setConfirmaBorrar(false)}>
                No
              </button>
            </>
          ) : (
            <button type="button" className="btn btn--peligro" onClick={() => setConfirmaBorrar(true)}>
              Eliminar
            </button>
          ))}
        <span className="acciones__espacio" />
        <button type="button" className="btn" onClick={onCerrar}>
          Cancelar
        </button>
        <button type="submit" className="btn btn--primario" disabled={guardando}>
          {guardando ? "Guardando…" : editando ? "Guardar cambios" : "Añadir parcela"}
        </button>
      </div>
    </form>
  );
}

export default function DialogoParcela({ abierto, planId, parcela, onCerrar, onGuardado }) {
  return (
    <Dialogo abierto={abierto} titulo={parcela ? "Editar parcela" : "Añadir parcela"} onCerrar={onCerrar}>
      <Formulario planId={planId} parcela={parcela} onGuardado={onGuardado} onCerrar={onCerrar} />
    </Dialogo>
  );
}
