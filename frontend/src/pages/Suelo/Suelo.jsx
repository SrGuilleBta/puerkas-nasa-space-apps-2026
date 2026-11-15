import { useState } from "react";

import {
  getActual,
  getAguaSubterranea,
  getCobertura,
  getErosion,
  getEstado,
  getHistorico,
  getPropiedades,
  getRaiz,
  getRetencion,
  getSmap,
} from "../../api/suelo.js";
import Cargable from "../../components/Cargable.jsx";
import { Brote, Gota, Suelo as IconoSuelo } from "../../components/Iconos.jsx";
import Tarjeta, { EncabezadoTarjeta } from "../../components/Tarjeta.jsx";
import useDatos from "../../hooks/useDatos.js";
import Escala from "./Escala.jsx";
import GraficaLinea from "./GraficaLinea.jsx";
import GraficaMeses from "./GraficaMeses.jsx";
import GraficaRetencion from "./GraficaRetencion.jsx";
import { AguaSubterranea, Montana } from "./IconosSuelo.jsx";
import {
  COLORES,
  TRAMOS_NDVI,
  TRAMOS_PENDIENTE,
  TRAMOS_SEQUIA,
  mesCompleto,
  resumenAgua,
  resumenAguaSubterranea,
  resumenPlantas,
  resumenTerreno,
  resumenTipoSuelo,
} from "./resumen.js";
import "./Suelo.css";

const ANIO_FIN = new Date().getFullYear() - 1;
const ANIO_INICIO = ANIO_FIN - 19;

function fechaPower(f) {
  // "20261111" -> "11/11/2026", "202401" -> "01/2024", "2026-11-13" -> "13/11/2026"
  if (!f) return "";
  if (f.includes("-")) return f.split("-").reverse().join("/");
  return f.length === 8 ? `${f.slice(6, 8)}/${f.slice(4, 6)}/${f.slice(0, 4)}` : `${f.slice(4, 6)}/${f.slice(0, 4)}`;
}

const mayuscula = (t) => (t ? t[0].toUpperCase() + t.slice(1) : "—");

function Dato({ etiqueta, valor, unidad }) {
  return (
    <div className="suelo-dato">
      <span className="suelo-dato__etiqueta">{etiqueta}</span>
      <span className="suelo-dato__valor">
        {valor ?? "—"}
        {valor != null && unidad ? <small> {unidad}</small> : null}
      </span>
    </div>
  );
}

function Fuente({ children }) {
  return <p className="suelo-fuente">Fuente: {children}</p>;
}

// Un cuadro del resumen simple: ícono, título con color y una frase. Se carga por su cuenta.
function Cuadro({ icono, etiqueta, estado, resumir, children }) {
  const r = estado.datos ? resumir(estado.datos) : null;
  return (
    <div className="resumen__cuadro">
      <p className="resumen__etiqueta">
        <span className="resumen__icono">{icono}</span> {etiqueta}
      </p>
      {estado.error ? (
        <p className="suelo-nota">No se pudo consultar. Intenta de nuevo en un momento.</p>
      ) : !estado.datos ? (
        <p className="suelo-nota">Consultando datos de satélite…</p>
      ) : !r ? (
        <p className="suelo-nota">Sin datos para este lugar.</p>
      ) : (
        <>
          <p className="resumen__titulo" style={{ color: COLORES[r.tono] }}>
            {r.titulo}
          </p>
          {r.frase && <p className="resumen__frase">{r.frase}</p>}
          {children?.(estado.datos)}
        </>
      )}
    </div>
  );
}

// useDatos (de Guille) conserva los datos anteriores mientras carga los nuevos. En Suelo eso hace que,
// al cambiar de estado, se sigan viendo los datos del estado anterior mientras llegan los nuevos (que
// pueden tardar). Aquí se ocultan mientras carga para que se vea "Consultando...".
function usarDatos(pedir, dependencias) {
  const e = useDatos(pedir, dependencias);
  return e.cargando ? { ...e, datos: null } : e;
}

// `municipio` es el ESTADO elegido en el selector de arriba (Layout). El backend usa el punto de campo
// de ese estado (services/municipios.py).
export default function Suelo({ municipio }) {
  const u = { municipio };
  const estado_ = municipio; // el selector ya es por estado
  const estado = usarDatos(() => getEstado(u), [municipio]);
  const actual = usarDatos(() => getActual(u), [municipio]);
  const smap = usarDatos(() => getSmap(u), [municipio]);
  const propiedades = usarDatos(() => getPropiedades(u), [municipio]);
  const erosion = usarDatos(() => getErosion(u), [municipio]);
  const agua = usarDatos(() => getAguaSubterranea(u), [municipio]);
  const historico = usarDatos(() => getHistorico(u, ANIO_INICIO, ANIO_FIN), [municipio]);
  const raiz = usarDatos(() => getRaiz(u), [municipio]);
  const retencion = usarDatos(() => getRetencion(u), [municipio]);
  const cobertura = usarDatos(() => getCobertura(u), [municipio]);
  const [verDetalle, setVerDetalle] = useState(false);

  return (
    <div className="suelo">
      <h1 className="sr-only">Suelo</h1>

      <div className="suelo__ancho">
        <Tarjeta className="resumen">
          <EncabezadoTarjeta etiqueta={`Datos de satélite de ${estado_}`} titulo="Así está tu suelo" />
          <div className="resumen__cuadros">
            <Cuadro icono={<Gota size={22} />} etiqueta="Agua en tu suelo" estado={estado} resumir={resumenAgua}>
              {(d) =>
                !d.mensaje && (
                  <Escala tramos={TRAMOS_SEQUIA} valor={d.percentil} extremos={["Muy seco", "Normal o húmedo"]} />
                )
              }
            </Cuadro>
            <Cuadro icono={<Brote size={22} />} etiqueta="Plantas en tu terreno" estado={cobertura} resumir={resumenPlantas}>
              {(d) =>
                d.ultimo && (
                  <Escala tramos={TRAMOS_NDVI} valor={d.ultimo.ndvi} min={0} max={1} extremos={["Pelón", "Muchas plantas"]} />
                )
              }
            </Cuadro>
            <Cuadro icono={<Montana size={22} />} etiqueta="Forma del terreno" estado={erosion} resumir={resumenTerreno}>
              {(d) => (
                <Escala
                  tramos={TRAMOS_PENDIENTE}
                  valor={d.terreno.pendiente_promedio_pct}
                  min={0}
                  max={30}
                  extremos={["Plano", "Muy inclinado"]}
                />
              )}
            </Cuadro>
            <Cuadro icono={<AguaSubterranea size={22} />} etiqueta="Agua bajo tierra en tu región" estado={agua} resumir={resumenAguaSubterranea}>
              {(d) => (
                <GraficaLinea
                  puntos={d.serie.map((p) => ({ x: p.fecha.slice(0, 4), y: p.anomalia_cm }))}
                  unidad="cm"
                  color="var(--tinta-suave)"
                  lineaCero
                  colorPorSigno
                  alto={140}
                />
              )}
            </Cuadro>
            <Cuadro icono={<IconoSuelo size={22} />} etiqueta="Tipo de suelo" estado={propiedades} resumir={resumenTipoSuelo} />
          </div>
          <p className="suelo-nota">
            Los colores siguen escalas oficiales: percentiles del Monitor de Sequía (agua), USGS (plantas), FAO
            (terreno).
          </p>
        </Tarjeta>
      </div>

      <div className="suelo__ancho suelo-detalle__boton">
        <button type="button" onClick={() => setVerDetalle((v) => !v)} aria-expanded={verDetalle}>
          {verDetalle ? "Ocultar detalle técnico ▲" : "Ver detalle técnico ▼"}
        </button>
      </div>

      {verDetalle && (
        <>

      <div className="suelo__ancho">
        <Cargable estado={estado} alto={150}>
          {(d) => (
            <Tarjeta className={`suelo-sequia ${d.categoria ? "suelo-sequia--seca" : ""}`}>
              <EncabezadoTarjeta etiqueta={`Suelo · datos de ${estado_}`} titulo="Humedad comparada con otros años" />
              {d.mensaje ? (
                <p className="suelo-nota">{d.mensaje}</p>
              ) : (
                <div className="suelo-sequia__cuerpo">
                  <div>
                    <span className="suelo-chip">{mayuscula(d.estado)}{d.categoria ? ` (equivale a ${d.categoria})` : ""}</span>
                    <p className="suelo-nota">
                      Últimos {d.periodo.dias} días ({fechaPower(d.periodo.inicio)} – {fechaPower(d.periodo.fin)}) contra el
                      mismo periodo de {d.anios_comparados} años ({d.mediciones_periodo} mediciones del satélite)
                    </p>
                    {d.pct_calidad_recomendada < 50 && (
                      <p className="suelo-aviso">
                        Solo {d.pct_calidad_recomendada} % de las mediciones tienen “calidad recomendada” por SMAP.
                      </p>
                    )}
                  </div>
                  <div className="suelo-datos">
                    <Dato etiqueta="Humedad (promedio 30 días)" valor={d.humedad_promedio} unidad="% vol." />
                    <Dato etiqueta="Promedio histórico" valor={d.promedio_historico_periodo} unidad="% vol." />
                    <Dato etiqueta="Percentil" valor={d.percentil} />
                  </div>
                </div>
              )}
              <p className="suelo-nota">
                Mide solo la humedad del suelo comparada con otros años. Usa los cortes por percentil del Monitor de
                Sequía como referencia, pero no es una declaración oficial de sequía (esa la da CONAGUA con más
                indicadores).
              </p>
              <Fuente>NASA SMAP (medición satelital, 9 km) · cortes por percentil del Drought Monitor</Fuente>
            </Tarjeta>
          )}
        </Cargable>
      </div>

      <Cargable estado={actual} alto={220}>
        {(d) => (
          <Tarjeta>
            <EncabezadoTarjeta etiqueta="Modelo NASA POWER" titulo="Humedad y temperatura" />
            <div className="suelo-datos">
              <Dato etiqueta="Superficie" valor={d.humedad_superficie} unidad="%" />
              <Dato etiqueta="Zona de raíz" valor={d.humedad_raiz} unidad="%" />
              <Dato etiqueta="Perfil" valor={d.humedad_perfil} unidad="%" />
              <Dato etiqueta="Temp. superficie" valor={d.temperatura_suelo} unidad="°C" />
              <Dato etiqueta="Evaporación" valor={d.evaporacion_mm_dia} unidad="mm/día" />
            </div>
            <p className="suelo-nota">% de saturación · dato del {fechaPower(d.fecha)} (POWER tiene 2–3 días de retraso)</p>
            <Fuente>NASA POWER (GWETTOP, GWETROOT, GWETPROF, TS, EVLAND)</Fuente>
          </Tarjeta>
        )}
      </Cargable>

      <Cargable estado={smap} alto={220}>
        {(d) => (
          <Tarjeta>
            <EncabezadoTarjeta etiqueta="Medición satelital" titulo="Humedad SMAP" />
            {d.ultima ? (
              <>
                <div className="suelo-datos">
                  <Dato etiqueta="Humedad superficial" valor={d.ultima.humedad_pct_volumen} unidad="% vol." />
                  <Dato etiqueta="Medición" valor={fechaPower(d.ultima.fecha)} />
                  <Dato etiqueta="Pasada" valor={d.ultima.pasada} />
                </div>
                {!d.ultima.calidad_recomendada && (
                  <p className="suelo-aviso">
                    SMAP marca esta medición como “calidad no recomendada” (p. ej. vegetación densa o interferencia).
                  </p>
                )}
                {d.serie.length > 1 && (
                  <GraficaLinea
                    puntos={d.serie.map((m) => ({ x: fechaPower(m.fecha).slice(0, 5), y: m.humedad_pct_volumen }))}
                    unidad="% vol."
                    color="var(--turquesa)"
                    alto={150}
                  />
                )}
              </>
            ) : (
              <p className="suelo-nota">El satélite no pasó por este punto en los últimos {d.dias_revisados} días.</p>
            )}
            <p className="suelo-nota">{d.nota}</p>
            <Fuente>{d.fuente}</Fuente>
          </Tarjeta>
        )}
      </Cargable>

      <Cargable estado={raiz} alto={220}>
        {(d) => (
          <Tarjeta>
            <EncabezadoTarjeta etiqueta="SMAP L4 · modelo corregido con satélite" titulo="Humedad en la raíz" />
            {d.ultima ? (
              <>
                <div className="suelo-datos">
                  <Dato etiqueta="Zona de raíces (0–100 cm)" valor={d.ultima.raiz_pct_volumen} unidad="% vol." />
                  <Dato etiqueta="Superficie (0–5 cm)" valor={d.ultima.superficie_pct_volumen} unidad="% vol." />
                  <Dato etiqueta="Fecha" valor={fechaPower(d.ultima.fecha)} />
                </div>
                {d.serie.length > 1 && (
                  <GraficaLinea
                    puntos={d.serie.map((m) => ({ x: fechaPower(m.fecha).slice(0, 5), y: m.raiz_pct_volumen }))}
                    unidad="% vol."
                    alto={150}
                  />
                )}
              </>
            ) : (
              <p className="suelo-nota">SMAP L4 no tiene datos recientes para este punto.</p>
            )}
            <p className="suelo-nota">{d.nota}</p>
            <Fuente>{d.fuente}</Fuente>
          </Tarjeta>
        )}
      </Cargable>

      <Cargable estado={cobertura} alto={220}>
        {(d) => (
          <Tarjeta>
            <EncabezadoTarjeta etiqueta="NASA MODIS · 250 m" titulo="Cobertura vegetal y suelo desnudo" />
            {d.ultimo && (
              <span className={`suelo-chip ${d.ultimo.ndvi <= 0.1 ? "suelo-chip--alerta" : ""}`}>
                Hoy: {mayuscula(d.ultimo.clase)} (NDVI {d.ultimo.ndvi})
              </span>
            )}
            <GraficaMeses meses={d.promedio_por_mes} />
            <p className="suelo-nota">
              {d.meses_suelo_desnudo.length
                ? `Meses con suelo desnudo (NDVI ≤ 0.1): ${d.meses_suelo_desnudo.map(mesCompleto).join(", ")}.`
                : "Ningún mes llega a suelo desnudo (NDVI ≤ 0.1)."}{" "}
              {d.mes_menor_cobertura &&
                `Menor cobertura en ${mesCompleto(d.mes_menor_cobertura.mes)} (NDVI ${d.mes_menor_cobertura.ndvi_promedio}). `}
              Promedio {d.anios_promediados}.
            </p>
            <Fuente>MODIS MOD13Q1 (NDVI) · clases del USGS</Fuente>
          </Tarjeta>
        )}
      </Cargable>

      <div className="suelo__ancho">
        <Cargable estado={retencion} alto={240}>
          {(d) => (
            <Tarjeta>
              <EncabezadoTarjeta etiqueta="Últimas semanas" titulo="Cómo retiene el agua el suelo" />
              <GraficaRetencion dias={d.dias} />
              <p className="suelo-nota">
                Cuando llueve, la humedad sube; si baja rápido, el suelo retiene poco el agua. {d.nota}
              </p>
              <Fuente>{d.fuente}</Fuente>
            </Tarjeta>
          )}
        </Cargable>
      </div>

      <div className="suelo__ancho">
        <Cargable estado={propiedades} alto={200}>
          {(d) => (
            <Tarjeta>
              <EncabezadoTarjeta etiqueta="SoilGrids · 250 m" titulo="Propiedades del suelo" />
              {d.sin_datos ? (
                <p className="suelo-nota">{d.aviso}</p>
              ) : (
                <div className="suelo-tabla">
                  <table>
                    <thead>
                      <tr>
                        <th>Profundidad</th>
                        <th>pH</th>
                        <th>Textura</th>
                        <th>Arcilla</th>
                        <th>Arena</th>
                        <th>Limo</th>
                        <th>Carbono org.</th>
                        <th>Materia org. (estimada)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.capas.map((c) => (
                        <tr key={c.profundidad}>
                          <td>{c.profundidad}</td>
                          <td>{c.ph ?? "—"}</td>
                          <td>{mayuscula(c.textura)}</td>
                          <td>{c.arcilla_pct ?? "—"} %</td>
                          <td>{c.arena_pct ?? "—"} %</td>
                          <td>{c.limo_pct ?? "—"} %</td>
                          <td>{c.carbono_organico_g_kg ?? "—"} g/kg</td>
                          <td>{c.materia_organica_estimada_pct ?? "—"} %</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <Fuente>
                SoilGrids (ISRIC) · textura: triángulo USDA · materia orgánica = carbono × 1.724 (Van Bemmelen,
                NOM-021-SEMARNAT-2000)
              </Fuente>
            </Tarjeta>
          )}
        </Cargable>
      </div>

      <Cargable estado={erosion} alto={220}>
        {(d) => (
          <Tarjeta>
            <EncabezadoTarjeta etiqueta="NASA SRTM · 30 m" titulo="Terreno y erosión" />
            <span className="suelo-chip suelo-chip--neutro">{mayuscula(d.clase_pendiente_fao)}</span>
            <div className="suelo-datos">
              <Dato etiqueta="Pendiente promedio" valor={d.terreno.pendiente_promedio_pct} unidad="%" />
              <Dato etiqueta="Pendiente máxima" valor={d.terreno.pendiente_maxima_pct} unidad="%" />
              <Dato etiqueta="Elevación" valor={d.terreno.elevacion_m} unidad="m" />
              <Dato etiqueta={`Días/año con lluvia ≥${d.lluvias_fuertes.umbral_mm} mm`} valor={d.lluvias_fuertes.dias_por_anio} />
              <Dato etiqueta="Lluvia máx. en un día" valor={d.lluvias_fuertes.lluvia_maxima_dia_mm} unidad="mm" />
              <Dato etiqueta="Factor LS (RUSLE)" valor={d.factor_ls.ls_promedio} />
              <Dato etiqueta="Factor LS máximo" valor={d.factor_ls.ls_maximo} />
            </div>
            <p className="suelo-nota">
              Factor LS: cuánto aumenta la forma del terreno la pérdida de suelo. {d.factor_ls.referencia}; un LS de 2
              significa el doble de pérdida, con todo lo demás igual.
            </p>
            <p className="suelo-nota">
              Pendiente en ~{d.terreno.area_analizada_m} m alrededor del punto · lluvias {d.lluvias_fuertes.periodo}
            </p>
            <Fuente>NASA SRTM + NASA POWER · clases de pendiente FAO · índice R20mm (OMM) · factor LS de la RUSLE (Moore y Burch, 1986)</Fuente>
          </Tarjeta>
        )}
      </Cargable>

      <Cargable estado={agua} alto={220}>
        {(d) => (
          <Tarjeta>
            <EncabezadoTarjeta etiqueta="NASA GRACE / GRACE-FO" titulo="Agua almacenada en la región" />
            <span className={`suelo-chip ${d.tendencia_cm_por_anio < 0 ? "suelo-chip--alerta" : ""}`}>
              {d.lectura}: {d.tendencia_cm_por_anio} cm/año
            </span>
            <GraficaLinea
              puntos={d.serie.map((p) => ({ x: p.fecha.slice(0, 7), y: p.anomalia_cm }))}
              unidad="cm"
              color="var(--invierno)"
              lineaCero
              colorPorSigno
            />
            <p className="suelo-nota">{d.nota}</p>
            <Fuente>JPL Mascon RL06.3</Fuente>
          </Tarjeta>
        )}
      </Cargable>

      <div className="suelo__ancho">
        <Cargable estado={historico} alto={220}>
          {(d) => (
            <Tarjeta>
              <EncabezadoTarjeta etiqueta="Tendencia" titulo={`Humedad en raíz ${ANIO_INICIO}–${ANIO_FIN}`} />
              <GraficaLinea puntos={d.serie.map((p) => ({ x: fechaPower(p.fecha), y: p.humedad_raiz }))} unidad="%" />
              <Fuente>NASA POWER (mensual)</Fuente>
            </Tarjeta>
          )}
        </Cargable>
      </div>

        </>
      )}

      <p className="suelo-nota suelo__ancho">
        Los datos son del estado de {estado_}: se usa el punto de campo más cercano a la capital donde hay datos de suelo (no la mancha
        urbana). Un estado es grande: el suelo y el clima cambian dentro de él. NASA POWER (~50 km), SMAP (9 km) y
        GRACE (~300 km) describen la región, no la parcela exacta.
      </p>
    </div>
  );
}
