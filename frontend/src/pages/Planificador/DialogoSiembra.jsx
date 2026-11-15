import { useId, useState } from "react";
import { borrarSiembra, crearCultivo, crearSiembra, editarSiembra } from "../../api/planificador.js";
import Dialogo from "../../components/Dialogo.jsx";
import { aISO, deISO, diasEntre, fechaConAnio, normalizar, sumarDias } from "../../utils/fechas.js";

const TIPOS = ["cereal", "leguminosa", "frutal", "hortaliza", "oleaginosa", "forraje", "otro"];
const AVISO_CICLO = 0.25; // se avisa si el periodo se aleja más de 25% del ciclo normal

// Primer día libre de la parcela: hoy, o el día siguiente a su última cosecha si aún no llega.
function primerDiaLibre(parcela, hoy) {
  const cosechas = parcela.siembras.map((s) => deISO(s.fechaCosecha));
  const ultima = cosechas.length ? new Date(Math.max(...cosechas)) : null;
  return ultima && sumarDias(ultima, 1) > hoy ? sumarDias(ultima, 1) : hoy;
}

// `sugerencia` = { cultivo, inicio } viene de una recomendación: deja el formulario ya lleno.
function Formulario({ parcela, siembra, sugerencia, cultivos, hoy, onGuardado, onCultivoCreado, onCerrar }) {
  const idLista = useId();
  const editando = Boolean(siembra);

  const [texto, setTexto] = useState(siembra?.cultivo.nombre ?? sugerencia?.cultivo ?? "");
  const [inicio, setInicio] = useState(siembra?.fechaSiembra ?? sugerencia?.inicio ?? aISO(primerDiaLibre(parcela, hoy)));
  // En una siembra nueva la cosecha se calcula sola con el ciclo; al editarla se respetan las fechas guardadas.
  const [fin, setFin] = useState(siembra?.fechaCosecha ?? "");
  const [finManual, setFinManual] = useState(editando);
  const [hectareas, setHectareas] = useState(String(siembra?.hectareas ?? parcela.hectareas));
  const [tipoNuevo, setTipoNuevo] = useState("");
  const [cicloNuevo, setCicloNuevo] = useState("");
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);

  const coincidencia = cultivos.find((c) => normalizar(c.nombre) === normalizar(texto));
  const esNuevo = texto.trim() !== "" && !coincidencia;
  // Cultivos del catálogo que se parecen a lo escrito: evita crear "maiz" teniendo "Maíz amarillo".
  const parecidos = esNuevo
    ? cultivos.filter((c) => normalizar(c.nombre).includes(normalizar(texto))).slice(0, 4)
    : [];
  const ciclo = coincidencia?.cicloDias ?? (esNuevo && Number(cicloNuevo) > 0 ? Number(cicloNuevo) : null);

  const finPropuesto = inicio && ciclo ? aISO(sumarDias(deISO(inicio), ciclo)) : "";
  const finEfectivo = finManual ? fin : finPropuesto;
  const duracion = inicio && finEfectivo ? diasEntre(deISO(inicio), deISO(finEfectivo)) : null;
  const lejosDelCiclo = ciclo && duracion > 0 && Math.abs(duracion - ciclo) / ciclo > AVISO_CICLO;

  function cambiarInicio(nuevo) {
    // Si la cosecha ya se fijó a mano, se mueve junto con la siembra para conservar la duración.
    if (finManual && fin && inicio && nuevo) {
      setFin(aISO(sumarDias(deISO(nuevo), diasEntre(deISO(inicio), deISO(fin)))));
    }
    setInicio(nuevo);
  }

  function validar() {
    if (!texto.trim()) return "Escribe el cultivo.";
    if (esNuevo && !tipoNuevo.trim()) return "Elige el tipo del cultivo nuevo.";
    if (esNuevo && !(Number(cicloNuevo) > 0)) return "Escribe el ciclo del cultivo nuevo en días.";
    if (!inicio || !finEfectivo) return "Indica la fecha de siembra y la de cosecha.";
    if (diasEntre(deISO(inicio), deISO(finEfectivo)) <= 0) return "La cosecha debe ser después de la siembra.";
    const ha = Number(hectareas);
    if (!(ha > 0)) return "Las hectáreas deben ser mayores a 0.";
    if (ha > parcela.hectareas) return `La parcela solo tiene ${parcela.hectareas} ha.`;
    return null;
  }

  async function guardar(e) {
    e.preventDefault();
    const problema = validar();
    if (problema) return setError(new Error(problema));

    setGuardando(true);
    setError(null);
    try {
      let cultivo = coincidencia;
      if (esNuevo) {
        try {
          cultivo = await crearCultivo({ nombre: texto.trim(), tipo: tipoNuevo, cicloDias: Number(cicloNuevo) });
        } catch (err) {
          if (err.estado === 409 && err.datos?.cultivo) cultivo = err.datos.cultivo; // ya existía
          else throw err;
        }
        onCultivoCreado();
      }
      const datos = {
        cultivoId: cultivo.id,
        fechaSiembra: inicio,
        fechaCosecha: finEfectivo,
        hectareas: Number(hectareas),
      };
      if (editando) await editarSiembra(siembra.id, datos);
      else await crearSiembra(parcela.id, datos);
      onGuardado();
    } catch (err) {
      setError(err);
    } finally {
      setGuardando(false);
    }
  }

  async function borrar() {
    setGuardando(true);
    try {
      await borrarSiembra(siembra.id);
      onGuardado();
    } catch (err) {
      setError(err);
      setConfirmaBorrar(false);
    } finally {
      setGuardando(false);
    }
  }

  const libreDesde = error?.datos?.libreDesde;

  return (
    <form className="formulario" onSubmit={guardar} noValidate>
      <p className="campo__ayuda">
        Parcela <b>{parcela.nombre}</b> · {parcela.hectareas} ha
      </p>

      <label className="campo">
        Cultivo
        <input
          list={idLista}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribe o elige uno"
          autoComplete="off"
          autoFocus={!editando}
        />
        <datalist id={idLista}>
          {cultivos.map((c) => (
            <option key={c.id} value={c.nombre} />
          ))}
        </datalist>
        {coincidencia && (
          <small>
            {coincidencia.tipo} · ciclo de {coincidencia.cicloDias} días
          </small>
        )}
      </label>

      {parecidos.length > 0 && (
        <div className="aviso aviso--info parecidos">
          ¿Quisiste decir…
          <span>
            {parecidos.map((c) => (
              <button key={c.id} type="button" onClick={() => setTexto(c.nombre)}>
                {c.nombre}
              </button>
            ))}
          </span>
        </div>
      )}

      {esNuevo && (
        <div className="formulario__nuevo">
          <b>
            «{texto.trim()}» no está en el catálogo.{" "}
            {parecidos.length > 0 ? "Si es otro cultivo, se agregará con estos datos:" : "Se agregará con estos datos:"}
          </b>
          <div className="campos">
            <label className="campo">
              Tipo
              <select value={tipoNuevo} onChange={(e) => setTipoNuevo(e.target.value)}>
                <option value="">Elige…</option>
                {TIPOS.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="campo">
              Ciclo (días)
              <input type="number" min="1" max="1500" value={cicloNuevo} onChange={(e) => setCicloNuevo(e.target.value)} />
            </label>
          </div>
        </div>
      )}

      <div className="campos">
        <label className="campo">
          Siembra
          <input type="date" value={inicio} onChange={(e) => cambiarInicio(e.target.value)} />
        </label>
        <label className="campo">
          Cosecha
          <input
            type="date"
            value={finEfectivo}
            onChange={(e) => {
              setFin(e.target.value);
              setFinManual(true);
            }}
          />
        </label>
      </div>

      {duracion > 0 && (
        <p className="campo__ayuda">
          Duración: <b>{duracion} días</b>
          {!finManual && finPropuesto && " (calculada con el ciclo del cultivo; puedes cambiarla)"}
        </p>
      )}
      {lejosDelCiclo && (
        <p className="aviso aviso--info">
          El ciclo normal de este cultivo es de {ciclo} días y este periodo dura {duracion}.
        </p>
      )}

      <label className="campo">
        Hectáreas sembradas
        <input type="number" step="0.1" min="0.1" value={hectareas} onChange={(e) => setHectareas(e.target.value)} />
      </label>

      {error && (
        <div className="aviso aviso--error" role="alert">
          {error.message}
          {libreDesde && (
            <button
              type="button"
              onClick={() => {
                cambiarInicio(libreDesde);
                setError(null);
              }}
            >
              Empezar el {fechaConAnio(deISO(libreDesde))}
            </button>
          )}
        </div>
      )}

      <div className="acciones">
        {editando &&
          (confirmaBorrar ? (
            <>
              <span className="campo__ayuda">¿Eliminar esta siembra?</span>
              <button type="button" className="btn btn--peligro" disabled={guardando} onClick={borrar}>
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
          {guardando ? "Guardando…" : editando ? "Guardar cambios" : "Añadir cultivo"}
        </button>
      </div>
    </form>
  );
}

export default function DialogoSiembra({ abierto, parcela, siembra, sugerencia, cultivos, hoy, onCerrar, onGuardado, onCultivoCreado }) {
  return (
    <Dialogo abierto={abierto} titulo={siembra ? "Editar cultivo" : "Añadir cultivo"} onCerrar={onCerrar}>
      {parcela && (
        <Formulario
          parcela={parcela}
          siembra={siembra}
          sugerencia={sugerencia}
          cultivos={cultivos}
          hoy={hoy}
          onGuardado={onGuardado}
          onCultivoCreado={onCultivoCreado}
          onCerrar={onCerrar}
        />
      )}
    </Dialogo>
  );
}
