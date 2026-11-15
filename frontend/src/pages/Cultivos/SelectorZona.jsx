import { Ubicacion } from "../../components/Iconos.jsx";

// Filtro de zona: todo México, un estado o un municipio. Con zona, los datos (rendimiento, precio,
// riesgos, siembra ideal y cuidados) salen de esa zona; sin ella, del país.
export default function SelectorZona({ estados, zona, onCambiar }) {
  const estado = estados.find((e) => e.clave === zona.estado);
  const municipios = estado?.municipios ?? [];

  return (
    <div className="enc__zona">
      <span className="enc__zona-icono">
        <Ubicacion size={18} />
      </span>

      <label className="enc__campo">
        <span>State</span>
        <select value={zona.estado} onChange={(e) => onCambiar({ estado: e.target.value, municipio: "" })}>
          <option value="">All of Mexico</option>
          {estados.map((e) => (
            <option key={e.clave} value={e.clave}>
              {e.nombre}
            </option>
          ))}
        </select>
      </label>

      <label className="enc__campo">
        <span>Municipality</span>
        <select
          value={zona.municipio}
          disabled={!estado}
          onChange={(e) => onCambiar({ estado: zona.estado, municipio: e.target.value })}
        >
          <option value="">{estado ? `All of ${estado.nombre}` : "Choose a state first"}</option>
          {municipios.map((m) => (
            <option key={m.clave} value={m.clave}>
              {m.nombre}
              {m.con_datos ? "" : " (no farm data)"}
            </option>
          ))}
        </select>
      </label>

      {(zona.estado || zona.municipio) && (
        <button type="button" className="enc__limpiar" onClick={() => onCambiar({ estado: "", municipio: "" })}>
          Clear
        </button>
      )}
    </div>
  );
}
