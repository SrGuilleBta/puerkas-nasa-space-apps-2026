import {
  getAlertaRegional,
  getAviso,
  getClima,
  getCultivoActivo,
  getPlanAnual,
} from "../../api/principal.js";
import Cargable from "../../components/Cargable.jsx";
import useDatos from "../../hooks/useDatos.js";
import AlertaRegional from "./AlertaRegional.jsx";
import BannerPreventivo from "./BannerPreventivo.jsx";
import CultivoActivo from "./CultivoActivo.jsx";
import PlanAnual from "./PlanAnual.jsx";
import PronosticoSemanal from "./PronosticoSemanal.jsx";
import "./Principal.css";

// Cada sección pide su dato por separado: se puede conectar una a la vez
// (ver src/api/principal.js) sin tocar las demás.
export default function Principal({ municipio }) {
  const aviso = useDatos(() => getAviso(municipio), [municipio]);
  const clima = useDatos(() => getClima(municipio), [municipio]);
  const alerta = useDatos(() => getAlertaRegional(municipio), [municipio]);
  const cultivo = useDatos(() => getCultivoActivo(municipio), [municipio]);
  const plan = useDatos(() => getPlanAnual(), []);

  return (
    <div className="principal">
      <h1 className="sr-only">Principal</h1>
      <div className="principal__aviso">
        <Cargable estado={aviso} alto={72}>
          {(d) => <BannerPreventivo {...d} />}
        </Cargable>
      </div>
      <div className="principal__columna">
        <Cargable estado={clima} alto={520}>
          {(d) => <PronosticoSemanal {...d} />}
        </Cargable>
        <Cargable estado={alerta} alto={100}>
          {(d) => <AlertaRegional {...d} />}
        </Cargable>
      </div>
      <div className="principal__columna">
        <Cargable estado={cultivo} alto={460}>
          {(d) => <CultivoActivo cultivo={d} />}
        </Cargable>
      </div>
      <div className="principal__plan">
        <Cargable estado={plan} alto={200}>
          {(d) => <PlanAnual plan={d} />}
        </Cargable>
      </div>
    </div>
  );
}
