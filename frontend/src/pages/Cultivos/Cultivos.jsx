import { useEffect, useMemo, useState } from "react";
import { getBiblioteca, getFicha, getZonaDeUbicacion, getZonas } from "../../api/cultivos.js";
import Cargable from "../../components/Cargable.jsx";
import useDatos from "../../hooks/useDatos.js";
import { guardarJSON, leerJSON, normalizar } from "../../utils/cultivos.js";
import Biblioteca from "./Biblioteca.jsx";
import FichaCultivo from "./FichaCultivo.jsx";
import SelectorZona from "./SelectorZona.jsx";
import "./Cultivos.css";

const CLAVES = { zona: "cultivosZona", elegido: "cultivoElegido", favoritos: "cultivosFavoritos" };
const ZONA_VACIA = { estado: "", municipio: "" }; // todo México
const ZONA_INICIAL = { estado: "19", municipio: "" }; // Nuevo León: si la ubicación activa no se puede ubicar en SIAP

// Zona de SIAP (estado/municipio) a partir de la respuesta de /api/cultivos/zona
const zonaDe = (z) => (z ? { estado: z.cve_ent, municipio: z.nivel === "municipality" ? z.clave : "" } : null);

// Enciclopedia de cultivos: la ficha del cultivo elegido (izquierda) y la biblioteca con buscador,
// filtro por tipo y favoritos (derecha). El filtro de zona (estado o municipio) cambia los datos
// y los cuidados a los de esa zona.
//
// La zona de arranque sale de la ubicación activa del proyecto (`ubicacion`: nombre y coordenadas):
// su municipio o, si no tiene correspondencia, su estado. Si la persona elige otra zona a mano, se
// recuerda mientras la ubicación activa siga siendo la misma.
export default function Cultivos({ ubicacion }) {
  const zonas = useDatos(getZonas, []);
  const [manual, setManual] = useState(() => leerJSON(CLAVES.zona, null)); // { ubicacion, zona }
  const nombreUbicacion = ubicacion?.nombre ?? null;
  const eligioAMano = manual?.ubicacion === nombreUbicacion && manual?.zona;
  const derivada = useDatos(
    () => (ubicacion && !eligioAMano ? getZonaDeUbicacion(ubicacion).catch(() => null) : Promise.resolve(null)),
    [nombreUbicacion, ubicacion?.lat, ubicacion?.lon, Boolean(eligioAMano)],
  );
  const resolviendo = !eligioAMano && (ubicacion === null || derivada.cargando);
  const zona = eligioAMano || zonaDe(derivada.datos) || ZONA_INICIAL;
  const setZona = (z) => setManual({ ubicacion: nombreUbicacion, zona: z });
  const [elegido, setElegido] = useState(() => leerJSON(CLAVES.elegido, null));
  const [favoritos, setFavoritos] = useState(() => leerJSON(CLAVES.favoritos, []));
  const [busqueda, setBusqueda] = useState("");
  const [tipo, setTipo] = useState("");
  const [soloFavoritos, setSoloFavoritos] = useState(false);
  const [soloAqui, setSoloAqui] = useState(false);

  const clave = zona.municipio || zona.estado || ""; // vacío = todo México
  const hayZona = clave !== "";
  const biblioteca = useDatos(() => (resolviendo ? Promise.resolve([]) : getBiblioteca(clave)), [clave, resolviendo]);
  const todos = biblioteca.datos ?? [];

  useEffect(() => {
    if (manual) guardarJSON(CLAVES.zona, manual);
  }, [manual]);
  useEffect(() => guardarJSON(CLAVES.favoritos, favoritos), [favoritos]);
  useEffect(() => {
    if (elegido) guardarJSON(CLAVES.elegido, elegido);
  }, [elegido]);

  const estados = zonas.datos?.estados ?? [];
  const estado = estados.find((e) => e.clave === zona.estado);
  const municipio = estado?.municipios.find((m) => m.clave === zona.municipio);
  const nombreZona = municipio ? `${municipio.nombre}, ${estado.nombre}` : (estado?.nombre ?? "Mexico");

  // Si la zona guardada ya no existe, se vuelve a todo México
  useEffect(() => {
    if (zonas.datos && zona.estado && !estado) setZona(ZONA_VACIA);
  }, [zonas.datos, estado, zona.estado]);

  const visibles = useMemo(() => {
    const q = normalizar(busqueda);
    const lista = todos.filter((c) => {
      if (tipo && c.tipo !== tipo) return false;
      if (soloFavoritos && !favoritos.includes(c.id)) return false;
      if (hayZona && soloAqui && !c.sembrado_en_ubicacion) return false;
      if (!q) return true;
      return [c.nombre, c.nombre_es, c.cientifico, c.id.replaceAll("-", " ")].some((t) => normalizar(t).includes(q));
    });
    // Favoritos primero; el resto conserva el orden del backend (por superficie sembrada)
    return [...lista.filter((c) => favoritos.includes(c.id)), ...lista.filter((c) => !favoritos.includes(c.id))];
  }, [todos, busqueda, tipo, soloFavoritos, soloAqui, hayZona, favoritos]);

  // El cultivo que se muestra: el elegido (aunque el filtro lo oculte de la lista) o el primero.
  const activo = todos.find((c) => c.id === elegido) ?? visibles[0] ?? todos[0] ?? null;
  const ficha = useDatos(() => (activo && !resolviendo ? getFicha(clave, activo.id) : Promise.resolve(null)), [clave, activo?.id, resolviendo]);

  // En pantallas angostas la ficha queda debajo de la biblioteca: al elegir un cultivo se baja a ella
  function elegir(id) {
    setElegido(id);
    if (!window.matchMedia("(max-width: 959px)").matches) return;
    const sinAnimar = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelector(".enc__detalle")?.scrollIntoView({ behavior: sinAnimar ? "auto" : "smooth", block: "start" });
  }

  const alternarFavorito = (id) =>
    setFavoritos((f) => (f.includes(id) ? f.filter((x) => x !== id) : [...f, id]));

  return (
    <div className="enc">
      <h1 className="sr-only">Crops</h1>

      <div className="enc__barra">
        <Cargable estado={zonas} alto={64}>
          {() => <SelectorZona estados={estados} zona={zona} onCambiar={setZona} />}
        </Cargable>
      </div>

      <div className="enc__detalle">
        {activo ? (
          <Cargable estado={ficha} alto={560}>
            {(d) => <FichaCultivo datos={d} />}
          </Cargable>
        ) : (
          // Mientras llega la lista (o si falla) se muestra su estado de carga o de error
          <Cargable estado={biblioteca} alto={560}>
            {() => null}
          </Cargable>
        )}
      </div>

      <div className="enc__lateral">
        <Cargable estado={biblioteca} alto={560}>
          {() => (
            <Biblioteca
              cultivos={visibles}
              total={todos.length}
              elegido={activo?.id}
              favoritos={favoritos}
              onElegir={elegir}
              onFavorito={alternarFavorito}
              busqueda={busqueda}
              onBusqueda={setBusqueda}
              tipo={tipo}
              onTipo={setTipo}
              soloFavoritos={soloFavoritos}
              onSoloFavoritos={setSoloFavoritos}
              hayZona={hayZona}
              soloAqui={soloAqui}
              onSoloAqui={setSoloAqui}
              nombreZona={nombreZona}
            />
          )}
        </Cargable>
      </div>
    </div>
  );
}
