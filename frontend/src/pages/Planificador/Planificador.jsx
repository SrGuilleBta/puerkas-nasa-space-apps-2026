import { useEffect, useState } from "react";
import { getAnalisis, getPlan, listarCultivos, listarPlanes } from "../../api/planificador.js";
import Cargable from "../../components/Cargable.jsx";
import Tarjeta from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";
import { guardarPlanActivo, leerPlanActivo } from "../../utils/planActivo.js";
import { cambiarZoom, mover, ventanaInicial } from "../../utils/ventana.js";
import Calendario from "./Calendario.jsx";
import Controles from "./Controles.jsx";
import DialogoParcela from "./DialogoParcela.jsx";
import DialogoPlan from "./DialogoPlan.jsx";
import DialogoSiembra from "./DialogoSiembra.jsx";
import Recomendaciones from "./Recomendaciones.jsx";
import Resumen from "./Resumen.jsx";
import "./Planificador.css";

const hoyLocal = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
};

export default function Planificador() {
  const planes = useDatos(listarPlanes, []);
  const cultivos = useDatos(listarCultivos, []);
  const [planElegido, setPlanElegido] = useState(leerPlanActivo);
  const [ventana, setVentana] = useState(() => ventanaInicial());
  // Qué popup está abierto: { tipo: "siembra" | "parcela" | "plan", ...datos } o null
  const [dialogo, setDialogo] = useState(null);
  const hoy = hoyLocal();

  // El plan que se muestra: el elegido o, si no hay, el primero.
  const planId = planElegido ?? planes.datos?.[0]?.id ?? null;
  const plan = useDatos(() => (planId ? getPlan(planId) : Promise.resolve(null)), [planId]);
  // Resumen del ciclo y recomendaciones: se recalculan cada vez que cambia el plan.
  const analisis = useDatos(() => (planId ? getAnalisis(planId) : Promise.resolve(null)), [planId]);

  // Si el plan guardado ya no existe (p. ej. otro navegador lo borró), se vuelve al primero.
  // Solo se revisa cuando llega una lista nueva: si dependiera también de `planElegido`, justo
  // después de crear un plan (con la lista aún vieja) desharía la selección del plan nuevo.
  useEffect(() => {
    if (planes.datos && planElegido && !planes.datos.some((p) => p.id === planElegido)) setPlanElegido(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planes.datos]);

  useEffect(() => {
    if (planElegido) guardarPlanActivo(planElegido);
  }, [planElegido]);

  const cerrar = () => setDialogo(null);
  const recargarPlan = () => {
    plan.recargar();
    analisis.recargar();
  };
  const guardado = () => {
    cerrar();
    recargarPlan();
  };

  function alGuardarPlan({ plan: p, borrado }) {
    cerrar();
    planes.recargar();
    if (borrado) setPlanElegido(null);
    else {
      setPlanElegido(p.id);
      recargarPlan();
    }
  }

  // "Añadir al plan" en una recomendación: abre el popup de cultivo ya lleno con la sugerencia.
  function anadirRecomendacion(r) {
    const parcela = plan.datos?.parcelas.find((p) => p.id === r.parcela.id);
    if (parcela) setDialogo({ tipo: "siembra", parcela, siembra: null, sugerencia: { cultivo: r.sugerido.nombre, inicio: r.desde } });
  }

  const planActual = planes.datos?.find((p) => p.id === planId) ?? null;

  return (
    <div className="planificador">
      <h1 className="planificador__titulo">Planificador</h1>

      <Cargable estado={planes} alto={90}>
        {(lista) =>
          lista.length === 0 ? (
            <Tarjeta className="planificador__vacio">
              <p>Todavía no tienes ningún plan.</p>
              <button type="button" className="btn btn--primario" onClick={() => setDialogo({ tipo: "plan", plan: null })}>
                Crear mi primer plan
              </button>
            </Tarjeta>
          ) : (
            <>
              <Tarjeta className="planificador__barra">
                <Controles
                  planes={lista}
                  planId={planId}
                  onPlan={setPlanElegido}
                  onNuevoPlan={() => setDialogo({ tipo: "plan", plan: null })}
                  onEditarPlan={() => setDialogo({ tipo: "plan", plan: planActual })}
                  meses={ventana.meses}
                  onMover={(sentido) => setVentana((v) => mover(v, sentido))}
                  onZoom={(sentido) => setVentana((v) => cambiarZoom(v, sentido))}
                  onHoy={() => setVentana((v) => ventanaInicial(v.meses))}
                />
              </Tarjeta>

              <Cargable estado={plan} alto={320}>
                {(p) =>
                  p && (
                    <Tarjeta className="planificador__calendario">
                      {p.parcelas.length === 0 ? (
                        <p className="planificador__aviso">Este plan aún no tiene parcelas. Añade la primera para empezar a planear.</p>
                      ) : (
                        <Calendario
                          plan={p}
                          ventana={ventana}
                          hoy={hoy}
                          onAgregarSiembra={(parcela) => setDialogo({ tipo: "siembra", parcela, siembra: null })}
                          onEditarSiembra={(parcela, siembra) => setDialogo({ tipo: "siembra", parcela, siembra })}
                          onEditarParcela={(parcela) => setDialogo({ tipo: "parcela", parcela })}
                        />
                      )}
                      <button type="button" className="btn planificador__parcela-nueva" onClick={() => setDialogo({ tipo: "parcela", parcela: null })}>
                        + Añadir parcela
                      </button>
                    </Tarjeta>
                  )
                }
              </Cargable>

              {plan.datos?.parcelas.length > 0 && (
                <div className="planificador__analisis">
                  <Cargable estado={analisis} alto={180}>
                    {(a) =>
                      a && (
                        <>
                          <Resumen resumen={a.resumen} />
                          <Recomendaciones recomendaciones={a.recomendaciones} onAnadir={anadirRecomendacion} />
                        </>
                      )
                    }
                  </Cargable>
                </div>
              )}
            </>
          )
        }
      </Cargable>

      <DialogoSiembra
        abierto={dialogo?.tipo === "siembra"}
        parcela={dialogo?.parcela}
        siembra={dialogo?.siembra}
        sugerencia={dialogo?.sugerencia}
        cultivos={cultivos.datos ?? []}
        hoy={hoy}
        onCerrar={cerrar}
        onGuardado={guardado}
        onCultivoCreado={cultivos.recargar}
      />
      <DialogoParcela
        abierto={dialogo?.tipo === "parcela"}
        planId={planId}
        parcela={dialogo?.parcela}
        onCerrar={cerrar}
        onGuardado={guardado}
      />
      <DialogoPlan abierto={dialogo?.tipo === "plan"} plan={dialogo?.plan} onCerrar={cerrar} onGuardado={alGuardarPlan} />
    </div>
  );
}
