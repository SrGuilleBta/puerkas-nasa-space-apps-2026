import { useId, useState } from "react";
import {
  borrarSiembra,
  crearCultivo,
  crearSiembra,
  cultivoDesdeCatalogo,
  editarSiembra,
  getCatalogo,
  getFichaCatalogo,
} from "../../api/planificador.js";
import Dialogo from "../../components/Dialogo.jsx";
import useDatos from "../../hooks/useDatos.js";
import InfoSiembra from "./InfoSiembra.jsx";
import VentanaSiembra from "./VentanaSiembra.jsx";
import { aISO, deISO, diasEntre, fechaConAnio, normalizar, sumarDias } from "../../utils/fechas.js";
import { numero, pesos } from "../../utils/formato.js";
import { TIPOS, etiquetaTipo } from "../../utils/tipos.js";

const dias = (n) => `${n} ${n === 1 ? "day" : "days"}`;
const AVISO_CICLO = 0.25; // se avisa si el periodo se aleja más de 25% del ciclo normal

// Primer día libre de la parcela: hoy, o el día siguiente a su última cosecha si aún no llega.
function primerDiaLibre(parcela, hoy) {
  const cosechas = parcela.siembras.map((s) => deISO(s.fechaCosecha));
  const ultima = cosechas.length ? new Date(Math.max(...cosechas)) : null;
  return ultima && sumarDias(ultima, 1) > hoy ? sumarDias(ultima, 1) : hoy;
}

// Texto de un campo numérico opcional -> número, o null si está vacío
const aNumero = (texto) => (String(texto).trim() === "" ? null : Number(texto));

// `sugerencia` = { cultivo, inicio } viene de una recomendación: deja el formulario ya lleno.
function Formulario({ parcela, siembra, sugerencia, cultivos, hoy, municipio, onGuardado, onCultivoCreado, onCerrar }) {
  const idLista = useId();
  const editando = Boolean(siembra);

  const [texto, setTexto] = useState(siembra?.cultivo.nombre ?? sugerencia?.cultivo ?? "");
  const [inicio, setInicio] = useState(siembra?.fechaSiembra ?? sugerencia?.inicio ?? aISO(primerDiaLibre(parcela, hoy)));
  // En una siembra nueva la cosecha se calcula sola con el ciclo; al editarla se respetan las fechas guardadas.
  const [fin, setFin] = useState(siembra?.fechaCosecha ?? "");
  const [finManual, setFinManual] = useState(editando);
  const [hectareas, setHectareas] = useState(String(siembra?.hectareas ?? parcela.hectareas));
  // Costos e ingresos (opcionales): rendimiento esperado, precio de venta y costo por hectárea
  const [rend, setRend] = useState(String(siembra?.rendimientoTHa ?? ""));
  const [precio, setPrecio] = useState(String(siembra?.precioT ?? ""));
  const [costo, setCosto] = useState(String(siembra?.costoHa ?? ""));
  const [tipoNuevo, setTipoNuevo] = useState("");
  const [cicloNuevo, setCicloNuevo] = useState("");
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);

  // Cultivos que ya tiene el Planificador y, además, los del catálogo de Cultivos que aún no se usan.
  // Elegir uno del catálogo lo agrega al Planificador al guardar (con su ficha de cuidados).
  const catalogo = useDatos(getCatalogo, []);
  const delCatalogo = (catalogo.datos ?? []).filter((c) => !cultivos.some((l) => normalizar(l.nombre) === normalizar(c.nombre)));
  const opciones = [...cultivos, ...delCatalogo];

  const local = cultivos.find((c) => normalizar(c.nombre) === normalizar(texto));
  const nuevoDelCatalogo = local ? null : delCatalogo.find((c) => normalizar(c.nombre) === normalizar(texto));
  const coincidencia = local ?? nuevoDelCatalogo;
  const esNuevo = texto.trim() !== "" && !coincidencia;

  // Cifras de partida para costos e ingresos (INIFAP del estado y mediana nacional); la persona las ajusta
  const catalogoId = local?.catalogoId ?? nuevoDelCatalogo?.id ?? null;
  const ficha = useDatos(() => (catalogoId ? getFichaCatalogo(catalogoId, municipio) : Promise.resolve(null)), [catalogoId, municipio]);
  const estimaciones = (ficha.datos?.estimaciones ?? []).slice(0, 4);
  const haNumero = Number(hectareas);
  const ingreso = aNumero(rend) != null && aNumero(precio) != null ? aNumero(rend) * aNumero(precio) * haNumero : null;
  const gasto = aNumero(costo) != null ? aNumero(costo) * haNumero : null;

  function usar(e) {
    if (e.rendimientoTHa != null) setRend(String(e.rendimientoTHa));
    if (e.precioT != null) setPrecio(String(e.precioT));
    if (e.costoHa != null) setCosto(String(e.costoHa));
  }
  // Cultivos que se parecen a lo escrito: evita crear "maiz" teniendo "Maíz grano".
  const parecidos = esNuevo
    ? opciones.filter((c) => normalizar(c.nombre).includes(normalizar(texto))).slice(0, 4)
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
    if (!texto.trim()) return "Enter the crop.";
    if (esNuevo && !tipoNuevo.trim()) return "Choose the type of the new crop.";
    if (esNuevo && !(Number(cicloNuevo) > 0)) return "Enter the new crop's cycle in days.";
    if (!inicio || !finEfectivo) return "Enter the planting date and the harvest date.";
    if (diasEntre(deISO(inicio), deISO(finEfectivo)) <= 0) return "The harvest must be after planting.";
    const ha = Number(hectareas);
    if (!(ha > 0)) return "Hectares must be greater than 0.";
    if (ha > parcela.hectareas) return `The plot only has ${parcela.hectareas} ha.`;
    for (const [texto, nombre] of [[rend, "yield"], [precio, "price"], [costo, "cost"]]) {
      const n = aNumero(texto);
      if (n != null && !(n >= 0)) return `The ${nombre} must be a number of 0 or more.`;
    }
    return null;
  }

  async function guardar(e) {
    e.preventDefault();
    const problema = validar();
    if (problema) return setError(new Error(problema));

    setGuardando(true);
    setError(null);
    try {
      let cultivo = local;
      if (nuevoDelCatalogo) {
        cultivo = await cultivoDesdeCatalogo(nuevoDelCatalogo.id);
        onCultivoCreado();
      } else if (esNuevo) {
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
        rendimientoTHa: aNumero(rend),
        precioT: aNumero(precio),
        costoHa: aNumero(costo),
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
        Plot <b>{parcela.nombre}</b> · {parcela.hectareas} ha
      </p>

      <label className="campo">
        Crop
        <input
          list={idLista}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Type or pick one"
          autoComplete="off"
          autoFocus={!editando}
        />
        <datalist id={idLista}>
          {opciones.map((c) => (
            <option key={c.id} value={c.nombre} />
          ))}
        </datalist>
        {coincidencia && (
          <small>
            {etiquetaTipo(coincidencia.tipo)} · {dias(coincidencia.cicloDias)} cycle
          </small>
        )}
      </label>

      {(local?.catalogoId ?? nuevoDelCatalogo?.id) && municipio && (
        <VentanaSiembra
          catalogoId={local?.catalogoId ?? nuevoDelCatalogo.id}
          municipio={municipio}
          mesInicio={inicio ? Number(inicio.slice(5, 7)) : null}
        />
      )}

      {parecidos.length > 0 && (
        <div className="aviso aviso--info parecidos">
          Did you mean…
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
            “{texto.trim()}” is not in the catalog.{" "}
            {parecidos.length > 0 ? "If it is a different crop, it will be added with these details:" : "It will be added with these details:"}
          </b>
          <div className="campos">
            <label className="campo">
              Type
              <select value={tipoNuevo} onChange={(e) => setTipoNuevo(e.target.value)}>
                <option value="">Choose…</option>
                {TIPOS.map((t) => (
                  <option key={t} value={t}>
                    {etiquetaTipo(t)}
                  </option>
                ))}
              </select>
            </label>
            <label className="campo">
              Cycle (days)
              <input type="number" min="1" max="1500" value={cicloNuevo} onChange={(e) => setCicloNuevo(e.target.value)} />
            </label>
          </div>
        </div>
      )}

      <div className="campos">
        <label className="campo">
          Planting
          <input type="date" value={inicio} onChange={(e) => cambiarInicio(e.target.value)} />
        </label>
        <label className="campo">
          Harvest
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
          Duration: <b>{dias(duracion)}</b>
          {!finManual && finPropuesto && " (calculated from the crop's cycle; you can change it)"}
        </p>
      )}
      {lejosDelCiclo && (
        <p className="aviso aviso--info">
          This crop's normal cycle is {dias(ciclo)} and this period lasts {dias(duracion)}.
        </p>
      )}

      <label className="campo">
        Hectares planted
        <input type="number" step="0.1" min="0.1" value={hectareas} onChange={(e) => setHectareas(e.target.value)} />
      </label>

      <fieldset className="economia-form">
        <legend>Estimated economics (optional)</legend>
        <div className="campos campos--tres">
          <label className="campo">
            Yield (t/ha)
            <input type="number" step="0.01" min="0" value={rend} onChange={(e) => setRend(e.target.value)} />
          </label>
          <label className="campo">
            Price (MXN/t)
            <input type="number" step="1" min="0" value={precio} onChange={(e) => setPrecio(e.target.value)} />
          </label>
          <label className="campo">
            Cost (MXN/ha)
            <input type="number" step="1" min="0" value={costo} onChange={(e) => setCosto(e.target.value)} />
          </label>
        </div>
        {estimaciones.length > 0 && (
          <div className="aviso aviso--info parecidos">
            Start from…
            <span>
              {estimaciones.map((e, i) => (
                <button key={i} type="button" onClick={() => usar(e)}>
                  {e.fuente}
                  {e.modalidad && ` (${e.modalidad === "riego" ? "irrigated" : "rainfed"})`}:{" "}
                  {[e.rendimientoTHa != null && `${numero(e.rendimientoTHa)} t/ha`, e.precioT != null && `${pesos(e.precioT)}/t`, e.costoHa != null && `${pesos(e.costoHa)}/ha`]
                    .filter(Boolean)
                    .join(" · ")}
                </button>
              ))}
            </span>
          </div>
        )}
        {(ingreso != null || gasto != null) && (
          <p className="campo__ayuda">
            {ingreso != null && <>Estimated income: <b>{pesos(ingreso)}</b>. </>}
            {gasto != null && <>Estimated cost: <b>{pesos(gasto)}</b>. </>}
            {ingreso != null && gasto != null && <>Profit: <b>{pesos(ingreso - gasto)}</b>.</>}
          </p>
        )}
        <p className="campo__ayuda">Estimates for planning, not a forecast. Leave blank what you do not know.</p>
      </fieldset>

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
              Start on {fechaConAnio(deISO(libreDesde))}
            </button>
          )}
        </div>
      )}

      <div className="acciones">
        {editando &&
          (confirmaBorrar ? (
            <>
              <span className="campo__ayuda">Delete this planting?</span>
              <button type="button" className="btn btn--peligro" disabled={guardando} onClick={borrar}>
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
          {guardando ? "Saving…" : editando ? "Save changes" : "Add crop"}
        </button>
      </div>
    </form>
  );
}

// Una siembra existente se abre en "Overview"; "Tasks" y "Crop guide" separan lo demás y "Edit" tiene el
// formulario. Una nueva va directo al formulario.
function Contenido({ parcela, siembra, ...resto }) {
  const [pestana, setPestana] = useState("resumen");
  if (!siembra) return <Formulario parcela={parcela} siembra={siembra} {...resto} />;

  return (
    <>
      <div className="pestanas" role="tablist">
        {[
          ["resumen", "Overview"],
          ["tareas", "Tasks"],
          ["guia", "Crop guide"],
          ["editar", "Edit"],
        ].map(([id, texto]) => (
          <button key={id} type="button" role="tab" aria-selected={pestana === id} onClick={() => setPestana(id)}>
            {texto}
          </button>
        ))}
      </div>
      {pestana !== "editar" ? (
        <>
          <InfoSiembra
            vista={pestana}
            parcela={parcela}
            siembra={siembra}
            hoy={resto.hoy}
            municipio={resto.municipio}
            onTareas={resto.onTareas}
          />
          <div className="acciones">
            <span className="acciones__espacio" />
            <button type="button" className="btn" onClick={resto.onCerrar}>
              Close
            </button>
            <button type="button" className="btn btn--primario" onClick={() => setPestana("editar")}>
              Edit
            </button>
          </div>
        </>
      ) : (
        <Formulario parcela={parcela} siembra={siembra} {...resto} />
      )}
    </>
  );
}

export default function DialogoSiembra({ abierto, parcela, siembra, sugerencia, cultivos, hoy, municipio, onCerrar, onGuardado, onCultivoCreado, onTareas }) {
  return (
    <Dialogo abierto={abierto} titulo={siembra ? siembra.cultivo.nombre : "Add crop"} onCerrar={onCerrar} amplio={Boolean(siembra)}>
      {parcela && (
        <Contenido
          parcela={parcela}
          siembra={siembra}
          sugerencia={sugerencia}
          cultivos={cultivos}
          hoy={hoy}
          municipio={municipio}
          onGuardado={onGuardado}
          onCultivoCreado={onCultivoCreado}
          onTareas={onTareas}
          onCerrar={onCerrar}
        />
      )}
    </Dialogo>
  );
}
