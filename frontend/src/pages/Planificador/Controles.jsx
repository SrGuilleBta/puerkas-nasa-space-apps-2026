import { useState } from "react";
import { Flecha, Mas, Menos } from "../../components/Iconos.jsx";
import { NIVELES_ZOOM } from "../../utils/ventana.js";

// Botón "Export PDF". Pide el archivo y lo descarga; si el servidor responde con un error, lo muestra en
// pantalla en vez de guardar la respuesta de error como si fuera el PDF (lo que haría un enlace de descarga).
function ExportarPdf({ href }) {
  const [estado, setEstado] = useState({ cargando: false, error: null });

  async function descargar() {
    setEstado({ cargando: true, error: null });
    try {
      const r = await fetch(href);
      if (!r.ok) {
        let mensaje = "";
        try {
          const { detail } = await r.json();
          mensaje = typeof detail === "string" ? detail : detail?.mensaje ?? "";
        } catch {
          /* la respuesta de error no traía JSON */
        }
        throw new Error(mensaje || `The PDF could not be created (error ${r.status}).`);
      }
      const nombre = /filename="([^"]+)"/.exec(r.headers.get("Content-Disposition") ?? "")?.[1] ?? "plan.pdf";
      const url = URL.createObjectURL(await r.blob());
      const enlace = Object.assign(document.createElement("a"), { href: url, download: nombre });
      enlace.click();
      URL.revokeObjectURL(url);
      setEstado({ cargando: false, error: null });
    } catch (e) {
      const sinServidor = e instanceof TypeError; // fetch falla con TypeError cuando no hay conexión
      setEstado({ cargando: false, error: sinServidor ? "Could not reach the server. Try again in a moment." : e.message });
    }
  }

  return (
    <>
      <button type="button" className="btn" onClick={descargar} disabled={estado.cargando}>
        {estado.cargando ? "Creating PDF…" : "Export PDF"}
      </button>
      {estado.error && (
        <p className="aviso aviso--error controles__error" role="alert">
          {estado.error}
        </p>
      )}
    </>
  );
}

// Selector de plan y controles del calendario (moverse en el tiempo y zoom).
export default function Controles({
  planes,
  planId,
  onPlan,
  onNuevoPlan,
  onEditarPlan,
  exportHref,
  exportPdfHref,
  meses,
  onMover,
  onZoom,
  onHoy,
}) {
  const i = NIVELES_ZOOM.indexOf(meses);
  return (
    <div className="controles">
      <div className="controles__plan">
        <label className="campo controles__selector">
          <span className="sr-only">Plan</span>
          <select value={planId ?? ""} onChange={(e) => onPlan(Number(e.target.value))}>
            {planes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="btn" onClick={onEditarPlan}>
          Edit plan
        </button>
        {exportHref && (
          <a className="btn" href={exportHref} download>
            Export CSV
          </a>
        )}
        {exportPdfHref && <ExportarPdf href={exportPdfHref} />}
        <button type="button" className="btn btn--primario" onClick={onNuevoPlan}>
          New plan
        </button>
      </div>

      <div className="controles__tiempo" role="group" aria-label="Calendar period">
        <button type="button" className="controles__icono controles__icono--atras" aria-label="Previous period" onClick={() => onMover(-1)}>
          <Flecha size={16} />
        </button>
        <button type="button" className="btn" onClick={onHoy}>
          Today
        </button>
        <button type="button" className="controles__icono" aria-label="Next period" onClick={() => onMover(1)}>
          <Flecha size={16} />
        </button>
        <span className="controles__zoom">
          <button type="button" className="controles__icono" aria-label="Show fewer months" disabled={i <= 0} onClick={() => onZoom(-1)}>
            <Mas size={16} />
          </button>
          <output>{meses} months</output>
          <button type="button" className="controles__icono" aria-label="Show more months" disabled={i >= NIVELES_ZOOM.length - 1} onClick={() => onZoom(1)}>
            <Menos size={16} />
          </button>
        </span>
      </div>
    </div>
  );
}
