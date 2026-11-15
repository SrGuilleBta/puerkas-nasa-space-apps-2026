import { useState } from "react";
import { getNoticias } from "../../api/noticias.js";
import Cargable from "../../components/Cargable.jsx";
import { Flecha } from "../../components/Iconos.jsx";
import Tarjeta from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";
import { SECCIONES, hashDe } from "../../routes.js";
import { deISO, fechaConAnio } from "../../utils/fechas.js";
import "./Noticias.css";

const FILTROS = [
  ["todas", "All"],
  ["farm", "My farm"],
  ["weather", "Weather"],
  ["research", "Research"],
];
const ETIQUETA = { farm: "My farm", weather: "Weather", research: "Research" };

function Noticia({ n }) {
  const interna = n.destino && !n.enlace;
  const nombreDestino = interna ? SECCIONES.find((s) => s.id === n.destino)?.nombre : null;
  return (
    <article className={`noticia noticia--${n.categoria}`}>
      <p className="noticia__etiqueta">{ETIQUETA[n.categoria]}</p>
      <h2 className="noticia__titulo">{n.titulo}</h2>
      {n.resumen && <p className="noticia__resumen">{n.resumen}</p>}
      <footer className="noticia__pie">
        <span>
          {n.fuente}
          {n.fecha && ` · ${fechaConAnio(deISO(n.fecha))}`}
        </span>
        {n.enlace && (
          <a href={n.enlace} target="_blank" rel="noopener noreferrer">
            Read more <Flecha size={14} />
          </a>
        )}
        {interna && (
          <a href={hashDe(n.destino)}>
            Open {nombreDestino} <Flecha size={14} />
          </a>
        )}
      </footer>
    </article>
  );
}

// Noticias: avisos propios calculados con tus datos y titulares de fuentes externas.
export default function Noticias({ municipio }) {
  const noticias = useDatos(() => getNoticias(municipio), [municipio]);
  const [filtro, setFiltro] = useState("todas");

  return (
    <div className="noticias">
      <h1 className="sr-only">News</h1>
      <div className="noticias__filtros" role="tablist" aria-label="Filter news">
        {FILTROS.map(([id, texto]) => (
          <button key={id} type="button" role="tab" aria-selected={filtro === id} onClick={() => setFiltro(id)}>
            {texto}
          </button>
        ))}
      </div>

      <Cargable estado={noticias} alto={320}>
        {({ items, externasCompletas }) => {
          const visibles = items.filter((n) => filtro === "todas" || n.categoria === filtro);
          return (
            <>
              {!externasCompletas && (
                <p className="aviso aviso--info">Some outside news sources are not available right now. Your own alerts are still up to date.</p>
              )}
              {visibles.length === 0 ? (
                <Tarjeta className="noticias__vacio">
                  <p>Nothing to show here right now.</p>
                </Tarjeta>
              ) : (
                <div className="noticias__lista">
                  {visibles.map((n) => (
                    <Noticia key={n.id} n={n} />
                  ))}
                </div>
              )}
            </>
          );
        }}
      </Cargable>
    </div>
  );
}
