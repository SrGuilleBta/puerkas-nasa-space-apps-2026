import { useEffect, useRef } from "react";
import { Brote, Buscar, Estrella } from "../../components/Iconos.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import { colorPorTexto } from "../../utils/colores.js";
import { textoCiclo } from "../../utils/cultivos.js";

// Tipos de la API, en el orden en que se ofrecen en el filtro.
export const TIPOS = ["Cereal", "Legume", "Fruit", "Vegetable", "Oilseed", "Forage", "Industrial", "Tuber", "Ornamental", "Seed", "Other"];

// Panel derecho del Figma: buscador y lista de cultivos con favoritos.
// El filtrado ya viene hecho (`cultivos`); aquí solo se muestran los controles y la lista.
export default function Biblioteca({
  cultivos, total, elegido, favoritos, onElegir, onFavorito,
  busqueda, onBusqueda, tipo, onTipo, soloFavoritos, onSoloFavoritos,
  hayZona, soloAqui, onSoloAqui, nombreZona,
}) {
  // Al abrir la página o cambiar de cultivo, la lista se desplaza para que el elegido quede a la vista
  const lista = useRef(null);
  useEffect(() => {
    const ul = lista.current;
    const fila = ul?.querySelector(".enc__fila--activa");
    if (!ul || !fila) return;
    if (fila.offsetTop < ul.scrollTop || fila.offsetTop + fila.offsetHeight > ul.scrollTop + ul.clientHeight) {
      ul.scrollTop = Math.max(0, fila.offsetTop - 8);
    }
  }, [elegido]);

  return (
    <Tarjeta className="enc__biblioteca">
      <EncabezadoTarjeta etiqueta="Library" titulo="Crops" derecha={<span className="enc__conteo">{cultivos.length} of {total}</span>} />

      <label className="enc__buscador">
        <Buscar size={18} />
        <span className="sr-only">Search crops</span>
        <input
          type="search"
          value={busqueda}
          placeholder="Search crop…"
          onChange={(e) => onBusqueda(e.target.value)}
          aria-describedby="enc-ayuda-busqueda"
        />
      </label>
      <p id="enc-ayuda-busqueda" className="enc__ayuda">
        Search by common name, scientific name or Spanish name.
      </p>

      <div className="enc__filtros">
        <label className="enc__campo enc__campo--corto">
          <span className="sr-only">Crop type</span>
          <select value={tipo} onChange={(e) => onTipo(e.target.value)}>
            <option value="">All types</option>
            {TIPOS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="enc__interruptor" aria-pressed={soloFavoritos} onClick={() => onSoloFavoritos(!soloFavoritos)}>
          <Estrella size={14} fill={soloFavoritos ? "currentColor" : "none"} /> Favorites
        </button>
        {hayZona && (
          <button
            type="button"
            className="enc__interruptor"
            aria-pressed={soloAqui}
            title={`Only crops grown in ${nombreZona}`}
            onClick={() => onSoloAqui(!soloAqui)}
          >
            Grown here
          </button>
        )}
      </div>

      {cultivos.length === 0 ? (
        <p className="enc__vacio">No crops match your search.</p>
      ) : (
        <ul className="enc__lista" ref={lista}>
          {cultivos.map((c) => {
            const esFavorito = favoritos.includes(c.id);
            const detalle = [c.tipo, textoCiclo(c.ciclo_dias, c.perenne)].filter(Boolean).join(" · ");
            return (
              <li key={c.id} className={`enc__fila ${c.id === elegido ? "enc__fila--activa" : ""}`}>
                <button
                  type="button"
                  className="enc__item"
                  aria-current={c.id === elegido ? "true" : undefined}
                  onClick={() => onElegir(c.id)}
                >
                  <span className="enc__icono" style={{ "--color": colorPorTexto(c.id) }}>
                    <Brote size={20} />
                  </span>
                  <span className="enc__textos">
                    <strong>{c.nombre}</strong>
                    <small>
                      {detalle}
                      {hayZona && !c.sembrado_en_ubicacion && " · not grown here"}
                    </small>
                  </span>
                </button>
                <button
                  type="button"
                  className={`enc__estrella ${esFavorito ? "enc__estrella--activa" : ""}`}
                  aria-pressed={esFavorito}
                  aria-label={`${esFavorito ? "Remove" : "Add"} ${c.nombre} ${esFavorito ? "from" : "to"} favorites`}
                  onClick={() => onFavorito(c.id)}
                >
                  <Estrella size={20} fill={esFavorito ? "currentColor" : "none"} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Tarjeta>
  );
}
