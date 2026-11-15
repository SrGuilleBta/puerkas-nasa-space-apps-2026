import { getNoticias } from "../../api/noticias.js";
import { getAlertas, getClima, getPlanificacion, getTareasVencidas } from "../../api/principal.js";
import Cargable from "../../components/Cargable.jsx";
import useDatos from "../../hooks/useDatos.js";
import AlertaRegional from "./AlertaRegional.jsx";
import BannerPreventivo from "./BannerPreventivo.jsx";
import CultivosActivos from "./CultivosActivos.jsx";
import PlanAnual from "./PlanAnual.jsx";
import PronosticoSemanal from "./PronosticoSemanal.jsx";
import TareasVencidas from "./TareasVencidas.jsx";
import "./Principal.css";

// Cada sección pide su dato por separado: se puede conectar una a la vez
// (ver src/api/principal.js) sin tocar las demás.
export default function Principal({ municipio }) {
  const clima = useDatos(() => getClima(municipio), [municipio]);
  const noticias = useDatos(() => getNoticias(municipio), [municipio]);
  // Cultivos activos y plan anual salen del mismo plan del Planificador, por eso van juntos.
  const planificacion = useDatos(() => getPlanificacion(municipio), [municipio]);
  // Las alertas dependen del clima y de los cultivos del plan que se está viendo
  const planId = planificacion.datos?.plan?.id;
  const aviso = useDatos(() => getAlertas(municipio, planId), [municipio, planId]);
  const tareas = useDatos(() => getTareasVencidas(planId), [planId]);

  return (
    <div className="principal">
      <h1 className="sr-only">Home</h1>
      <div className="principal__aviso">
        <Cargable estado={aviso} alto={72}>
          {(d) => <BannerPreventivo alertas={d} />}
        </Cargable>
        {/* Si las tareas fallan o no hay vencidas, el aviso simplemente no aparece */}
        {tareas.datos && !tareas.error && <TareasVencidas {...tareas.datos} />}
      </div>
      <div className="principal__columna">
        <Cargable estado={clima} alto={520}>
          {(d) => <PronosticoSemanal {...d} />}
        </Cargable>
        {/* Si las noticias fallan, la tarjeta simplemente no aparece (no es un dato esencial) */}
        {!noticias.error && (
          <Cargable estado={noticias} alto={100}>
            {({ items }) => {
              const noticia = items.find((n) => n.enlace) ?? items[0];
              return noticia && <AlertaRegional noticia={noticia} />;
            }}
          </Cargable>
        )}
      </div>
      <div className="principal__columna">
        <Cargable estado={planificacion} alto={460}>
          {(d) => <CultivosActivos activos={d.activos} />}
        </Cargable>
      </div>
      <div className="principal__plan">
        <Cargable estado={planificacion} alto={200}>
          {(d) => <PlanAnual plan={d.plan} />}
        </Cargable>
      </div>
    </div>
  );
}
