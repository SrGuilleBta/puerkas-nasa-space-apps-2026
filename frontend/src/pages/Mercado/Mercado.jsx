import { useEffect, useMemo, useState } from "react";
import { getEstadosMercado, getProductosMercado, getSerieMercado } from "../../api/mercado.js";
import Cargable from "../../components/Cargable.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";
import { deISO, fechaConAnio } from "../../utils/fechas.js";
import GraficaPrecios from "./GraficaPrecios.jsx";
import "./Mercado.css";

const COLORES = ["#0a7a4b", "#2563eb", "#d97706", "#9333ea", "#dc2626", "#0891b2", "#db2777", "#65a30d", "#4f46e5", "#ea580c"];
const RANGOS = [
  ["semana", "1 week"],
  ["mes", "1 month"],
  ["anio", "1 year"],
];
const INICIALES = ["JITOMATE", "LIMON", "AGUACATE"]; // si existen en el estado, arrancan marcados
const CLAVE_FAVORITOS = "mercado_favoritos";

const titulo = (texto) => texto.toLowerCase().replace(/(^|[\s(/])([a-z])/g, (_, a, b) => a + b.toUpperCase());
const signo = (n) => `${n > 0 ? "+" : ""}${n}%`;

function leerFavoritos() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_FAVORITOS)) ?? [];
  } catch {
    return [];
  }
}

function Cambio({ valor }) {
  if (valor == null) return null;
  return <small className={`mercado__cambio mercado__cambio--${valor > 0 ? "sube" : valor < 0 ? "baja" : "igual"}`}>{signo(valor)}</small>;
}

// Los que más subieron y más bajaron en los últimos 30 días de datos reales
function Oportunidades({ productos, fecha }) {
  const con = productos.filter((p) => p.cambio30dPct != null);
  if (con.length === 0) return null;
  const sube = con.reduce((a, b) => (b.cambio30dPct > a.cambio30dPct ? b : a));
  const baja = con.reduce((a, b) => (b.cambio30dPct < a.cambio30dPct ? b : a));
  const f = fecha ? fechaConAnio(deISO(fecha)) : "";
  return (
    <div className="mercado__destacados">
      <article>
        <p className="mercado__etiqueta">Biggest rise</p>
        <h3>{titulo(sube.nombre)}</h3>
        <p>
          <Cambio valor={sube.cambio30dPct} /> in the 30 days to {f}
        </p>
      </article>
      <article>
        <p className="mercado__etiqueta">Biggest drop</p>
        <h3>{titulo(baja.nombre)}</h3>
        <p>
          <Cambio valor={baja.cambio30dPct} /> in the 30 days to {f}
        </p>
      </article>
    </div>
  );
}

function Contenido({ municipio, datosEstados }) {
  const [manual, setManual] = useState(null);
  useEffect(() => setManual(null), [municipio]); // al cambiar de ubicación vuelve su estado
  const estado = manual ?? datosEstados.sugerido ?? datosEstados.estados[0].clave;

  const [rango, setRango] = useState("mes");
  const [busqueda, setBusqueda] = useState("");
  const [combinadas, setCombinadas] = useState(true);
  const [soloFavoritos, setSoloFavoritos] = useState(false);
  const [favoritos, setFavoritos] = useState(leerFavoritos);
  const [elegidos, setElegidos] = useState([]);

  useEffect(() => {
    try {
      localStorage.setItem(CLAVE_FAVORITOS, JSON.stringify(favoritos));
    } catch {
      /* sin almacenamiento: los favoritos duran hasta cerrar la pestaña */
    }
  }, [favoritos]);

  const productos = useDatos(() => getProductosMercado(estado), [estado]);
  const lista = productos.datos?.productos ?? [];

  // Al cargar un estado: se conservan los productos marcados que existan y, si no queda ninguno, arrancan los iniciales
  useEffect(() => {
    if (lista.length === 0) return;
    setElegidos((previos) => {
      const ids = new Set(lista.map((p) => p.id));
      const quedan = previos.filter((p) => ids.has(p));
      if (quedan.length > 0) return quedan;
      const iniciales = INICIALES.filter((p) => ids.has(p)).slice(0, 2);
      return iniciales.length > 0 ? iniciales : [lista[0].id];
    });
  }, [productos.datos]);

  const serie = useDatos(
    () => (elegidos.length > 0 && lista.length > 0 ? getSerieMercado(estado, elegidos, rango) : Promise.resolve(null)),
    [estado, elegidos.join(","), rango, productos.datos],
  );

  const visibles = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    return lista
      .filter((p) => (!q || p.nombre.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)) && (!soloFavoritos || favoritos.includes(p.id)))
      .sort((a, b) => Number(favoritos.includes(b.id)) - Number(favoritos.includes(a.id)) || a.nombre.localeCompare(b.nombre, "en"));
  }, [lista, busqueda, soloFavoritos, favoritos]);

  const color = (id) => COLORES[Math.max(0, elegidos.indexOf(id)) % COLORES.length];
  const alternar = (id) => setElegidos((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length >= COLORES.length ? p : [...p, id]));
  const alternarFavorito = (id) => setFavoritos((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  const series = (serie.datos?.productos ?? []).map((s) => ({ ...s, nombre: titulo(s.nombre), color: color(s.id) }));
  const d = productos.datos;

  return (
    <>
      <Tarjeta className="mercado__controles">
        <EncabezadoTarjeta
          etiqueta="Market"
          titulo="Retail price trends"
          derecha={
            <select aria-label="State" value={estado} onChange={(e) => setManual(e.target.value)} className="mercado__estado">
              {datosEstados.estados.map((e) => (
                <option key={e.clave} value={e.clave}>
                  {titulo(e.nombreEn)}
                </option>
              ))}
            </select>
          }
        />
        <div className="mercado__rangos" role="tablist" aria-label="Time range">
          {RANGOS.map(([id, texto]) => (
            <button key={id} type="button" role="tab" aria-selected={rango === id} onClick={() => setRango(id)}>
              {texto}
            </button>
          ))}
          <label className="mercado__interruptor">
            <input type="checkbox" checked={combinadas} onChange={(e) => setCombinadas(e.target.checked)} />
            Combined chart
          </label>
        </div>
        {datosEstados.desactualizado && (
          <p className="aviso aviso--info" role="status">
            The latest real prices are from <b>{fechaConAnio(deISO(datosEstados.ultimoDatoReal))}</b> ({datosEstados.diasSinDatos} days ago).
            After that date the dashed lines are a projection, not real prices.
          </p>
        )}
        {d && <Oportunidades productos={lista} fecha={d.ultimoDatoReal} />}
      </Tarjeta>

      <div className="mercado__cuerpo">
        <Tarjeta className="mercado__productos">
          <input
            type="search"
            className="mercado__buscar"
            placeholder="Search products"
            aria-label="Search products"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
          <label className="mercado__interruptor">
            <input type="checkbox" checked={soloFavoritos} onChange={(e) => setSoloFavoritos(e.target.checked)} />
            Favorites only
          </label>
          <Cargable estado={productos} alto={160}>
            {() => (
              <ul className="mercado__lista">
                {visibles.length === 0 && <li className="mercado__nota">No products match.</li>}
                {visibles.map((p) => (
                  <li key={p.id}>
                    <label>
                      <input type="checkbox" checked={elegidos.includes(p.id)} onChange={() => alternar(p.id)} />
                      <i className="mercado__color" style={{ background: elegidos.includes(p.id) ? color(p.id) : "transparent" }} />
                      <span className="mercado__nombre">{titulo(p.nombre)}</span>
                      <span className="mercado__precio">
                        {p.precio != null ? `$${p.precio.toFixed(1)}` : "—"}
                        <Cambio valor={p.cambio30dPct} />
                      </span>
                    </label>
                    <button
                      type="button"
                      className={`mercado__estrella${favoritos.includes(p.id) ? " mercado__estrella--activa" : ""}`}
                      aria-pressed={favoritos.includes(p.id)}
                      aria-label={`${favoritos.includes(p.id) ? "Remove" : "Add"} ${titulo(p.nombre)} ${favoritos.includes(p.id) ? "from" : "to"} favorites`}
                      onClick={() => alternarFavorito(p.id)}
                    >
                      ★
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Cargable>
        </Tarjeta>

        <Tarjeta className="mercado__graficas">
          {elegidos.length === 0 ? (
            <p className="mercado__nota">Pick one or more products to see their prices.</p>
          ) : (
            <Cargable estado={serie} alto={260}>
              {() => (
                <>
                  <p className="mercado__nota">
                    MXN per kilo at the supermarket (Profeco) · solid line: real price · dashed line: projection
                  </p>
                  {combinadas ? (
                    <>
                      <ul className="mercado__leyenda">
                        {series.map((s) => (
                          <li key={s.id}>
                            <i style={{ background: s.color }} />
                            {s.nombre}
                          </li>
                        ))}
                      </ul>
                      <GraficaPrecios series={series} ultimoReal={serie.datos.ultimoDatoReal} />
                    </>
                  ) : (
                    series.map((s) => (
                      <section key={s.id} className="mercado__una">
                        <h3>
                          <i style={{ background: s.color }} />
                          {s.nombre}
                        </h3>
                        <GraficaPrecios series={[s]} ultimoReal={serie.datos.ultimoDatoReal} />
                      </section>
                    ))
                  )}
                  <small className="mercado__nota">
                    Source: {serie.datos.fuente}. These are consumer prices, not farm-gate prices. The projection follows the
                    usual seasonal pattern and the recent price level, with simulated short-term variation: it does not know
                    about weather, supply or events.
                  </small>
                </>
              )}
            </Cargable>
          )}
        </Tarjeta>
      </div>
    </>
  );
}

// Pantalla Market: precios al consumidor (Profeco) por estado, con su proyección.
export default function Mercado({ municipio }) {
  const estados = useDatos(() => getEstadosMercado(municipio), [municipio]);
  return (
    <div className="mercado">
      <Cargable estado={estados} alto={200}>
        {(datos) => <Contenido municipio={municipio} datosEstados={datos} />}
      </Cargable>
    </div>
  );
}
