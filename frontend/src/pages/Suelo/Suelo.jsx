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
import Ayuda from "./Ayuda.jsx";
import Escala from "./Escala.jsx";
import GraficaLinea from "./GraficaLinea.jsx";
import GraficaMeses from "./GraficaMeses.jsx";
import GraficaRetencion from "./GraficaRetencion.jsx";
import MapaSuelo from "./MapaSuelo.jsx";
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
  return <p className="suelo-fuente">Source: {children}</p>;
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
        <p className="suelo-nota">Could not load. Please try again in a moment.</p>
      ) : !estado.datos ? (
        <p className="suelo-nota">Loading satellite data…</p>
      ) : !r ? (
        <p className="suelo-nota">No data for this place.</p>
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

// useDatos conserva los datos anteriores mientras carga los nuevos. En Suelo eso hace que, al cambiar
// de ubicación, se sigan viendo los datos anteriores mientras llegan los nuevos (que pueden tardar).
// Aquí se ocultan mientras carga para que se vea "Loading...".
function usarDatos(pedir, dependencias) {
  const e = useDatos(pedir, dependencias);
  return e.cargando ? { ...e, datos: null } : e;
}

// `ubicacion` es la ubicación elegida en el selector de arriba (tabla `ubicacion`, ver backend/app/db.py).
// El backend usa su punto de suelo (de cultivo) o, si no tiene, busca el cultivo más cercano con MODIS.
export default function Suelo({ ubicacion }) {
  const nombre = ubicacion.nombre;
  const u = { municipio: nombre };
  const estado = usarDatos(() => getEstado(u), [nombre]);
  const actual = usarDatos(() => getActual(u), [nombre]);
  const smap = usarDatos(() => getSmap(u), [nombre]);
  const propiedades = usarDatos(() => getPropiedades(u), [nombre]);
  const erosion = usarDatos(() => getErosion(u), [nombre]);
  const agua = usarDatos(() => getAguaSubterranea(u), [nombre]);
  const historico = usarDatos(() => getHistorico(u, ANIO_INICIO, ANIO_FIN), [nombre]);
  const raiz = usarDatos(() => getRaiz(u), [nombre]);
  const retencion = usarDatos(() => getRetencion(u), [nombre]);
  const cobertura = usarDatos(() => getCobertura(u), [nombre]);
  const [verDetalle, setVerDetalle] = useState(false);

  return (
    <div className="suelo">
      <h1 className="sr-only">Soil</h1>

      <div className="suelo__ancho">
        <Tarjeta className="resumen">
          <EncabezadoTarjeta etiqueta={`Satellite data · ${nombre}`} titulo="How your soil is doing" />
          <div className="resumen__cuadros">
            <Cuadro icono={<Gota size={22} />} etiqueta="Water in your soil" estado={estado} resumir={resumenAgua}>
              {(d) =>
                !d.mensaje && (
                  <Escala tramos={TRAMOS_SEQUIA} valor={d.percentil} extremos={["Very dry", "Normal or wet"]} />
                )
              }
            </Cuadro>
            <Cuadro icono={<Brote size={22} />} etiqueta="Plants on your land" estado={cobertura} resumir={resumenPlantas}>
              {(d) =>
                d.ultimo && (
                  <Escala tramos={TRAMOS_NDVI} valor={d.ultimo.ndvi} min={0} max={1} extremos={["Bare", "Many plants"]} />
                )
              }
            </Cuadro>
            <Cuadro icono={<Montana size={22} />} etiqueta="Shape of the land" estado={erosion} resumir={resumenTerreno}>
              {(d) => (
                <Escala
                  tramos={TRAMOS_PENDIENTE}
                  valor={d.terreno.pendiente_promedio_pct}
                  min={0}
                  max={30}
                  extremos={["Flat", "Very steep"]}
                />
              )}
            </Cuadro>
            <Cuadro icono={<AguaSubterranea size={22} />} etiqueta="Underground water in your region" estado={agua} resumir={resumenAguaSubterranea}>
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
            <Cuadro icono={<IconoSuelo size={22} />} etiqueta="Soil type" estado={propiedades} resumir={resumenTipoSuelo} />
          </div>
          <p className="suelo-nota">
            Colors follow official scales: Drought Monitor percentiles (water), USGS (plants), FAO (land).
          </p>
        </Tarjeta>
      </div>

      <div className="suelo__ancho">
        <MapaSuelo municipio={nombre} />
      </div>

      <div className="suelo__ancho suelo-detalle__boton">
        <button type="button" onClick={() => setVerDetalle((v) => !v)} aria-expanded={verDetalle}>
          {verDetalle ? "Hide technical details ▲" : "Show technical details ▼"}
        </button>
      </div>

      {verDetalle && (
        <>
          <div className="suelo__ancho">
            <Cargable estado={estado} alto={150}>
              {(d) => (
                <Tarjeta className={`suelo-sequia ${d.categoria ? "suelo-sequia--seca" : ""}`}>
                  <EncabezadoTarjeta etiqueta={`Soil · ${nombre}`} titulo="Soil moisture compared with other years" />
                  <Ayuda termino="percentil" />
                  {d.mensaje ? (
                    <p className="suelo-nota">{d.mensaje}</p>
                  ) : (
                    <div className="suelo-sequia__cuerpo">
                      <div>
                        <span className="suelo-chip">
                          {mayuscula(d.estado)}
                          {d.categoria ? ` (equivalent to ${d.categoria})` : ""}
                        </span>
                        <p className="suelo-nota">
                          Last {d.periodo.dias} days ({fechaPower(d.periodo.inicio)} – {fechaPower(d.periodo.fin)}) vs. the
                          same period of {d.anios_comparados} years ({d.mediciones_periodo} satellite measurements)
                        </p>
                        {d.pct_calidad_recomendada < 50 && (
                          <p className="suelo-aviso">
                            Only {d.pct_calidad_recomendada} % of the measurements have SMAP “recommended quality”.
                          </p>
                        )}
                      </div>
                      <div className="suelo-datos">
                        <Dato etiqueta="Moisture (30-day average)" valor={d.humedad_promedio} unidad="% vol." />
                        <Dato etiqueta="Historical average" valor={d.promedio_historico_periodo} unidad="% vol." />
                        <Dato etiqueta="Percentile" valor={d.percentil} />
                      </div>
                    </div>
                  )}
                  <p className="suelo-nota">
                    Measures only soil moisture compared with other years. It uses the Drought Monitor percentile cuts as a
                    reference, but it is not an official drought declaration (CONAGUA issues that one with more
                    indicators).
                  </p>
                  <Fuente>NASA SMAP (satellite measurement, 9 km) · Drought Monitor percentile cuts</Fuente>
                </Tarjeta>
              )}
            </Cargable>
          </div>

          <Cargable estado={actual} alto={220}>
            {(d) => (
              <Tarjeta>
                <EncabezadoTarjeta etiqueta="NASA POWER model" titulo="Moisture and temperature" />
                <Ayuda termino="modelo" />
                <Ayuda termino="evaporacion" />
                <div className="suelo-datos">
                  <Dato etiqueta="Surface" valor={d.humedad_superficie} unidad="%" />
                  <Dato etiqueta="Root zone" valor={d.humedad_raiz} unidad="%" />
                  <Dato etiqueta="Profile" valor={d.humedad_perfil} unidad="%" />
                  <Dato etiqueta="Surface temp." valor={d.temperatura_suelo} unidad="°C" />
                  <Dato etiqueta="Evaporation" valor={d.evaporacion_mm_dia} unidad="mm/day" />
                </div>
                <p className="suelo-nota">% of saturation · data from {fechaPower(d.fecha)} (POWER has a 2–3 day delay)</p>
                <Fuente>NASA POWER (GWETTOP, GWETROOT, GWETPROF, TS, EVLAND)</Fuente>
              </Tarjeta>
            )}
          </Cargable>

          <Cargable estado={smap} alto={220}>
            {(d) => (
              <Tarjeta>
                <EncabezadoTarjeta etiqueta="Satellite measurement" titulo="SMAP moisture" />
                <Ayuda termino="smap" />
                {d.ultima ? (
                  <>
                    <div className="suelo-datos">
                      <Dato etiqueta="Surface moisture" valor={d.ultima.humedad_pct_volumen} unidad="% vol." />
                      <Dato etiqueta="Measured" valor={fechaPower(d.ultima.fecha)} />
                      <Dato etiqueta="Pass" valor={d.ultima.pasada} />
                    </div>
                    {!d.ultima.calidad_recomendada && (
                      <p className="suelo-aviso">
                        SMAP flags this measurement as “quality not recommended” (e.g. dense vegetation or interference).
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
                  <p className="suelo-nota">The satellite did not pass over this point in the last {d.dias_revisados} days.</p>
                )}
                <p className="suelo-nota">{d.nota}</p>
                <Fuente>{d.fuente}</Fuente>
              </Tarjeta>
            )}
          </Cargable>

          <Cargable estado={raiz} alto={220}>
            {(d) => (
              <Tarjeta>
                <EncabezadoTarjeta etiqueta="SMAP L4 · model corrected with satellite" titulo="Root-zone moisture" />
                <Ayuda termino="raiz" />
                {d.ultima ? (
                  <>
                    <div className="suelo-datos">
                      <Dato etiqueta="Root zone (0–100 cm)" valor={d.ultima.raiz_pct_volumen} unidad="% vol." />
                      <Dato etiqueta="Surface (0–5 cm)" valor={d.ultima.superficie_pct_volumen} unidad="% vol." />
                      <Dato etiqueta="Date" valor={fechaPower(d.ultima.fecha)} />
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
                  <p className="suelo-nota">SMAP L4 has no recent data for this point.</p>
                )}
                <p className="suelo-nota">{d.nota}</p>
                <Fuente>{d.fuente}</Fuente>
              </Tarjeta>
            )}
          </Cargable>

          <Cargable estado={cobertura} alto={220}>
            {(d) => (
              <Tarjeta>
                <EncabezadoTarjeta etiqueta="NASA MODIS · 250 m" titulo="Plant cover and bare soil" />
                <Ayuda termino="ndvi" />
                {d.ultimo && (
                  <span className={`suelo-chip ${d.ultimo.ndvi <= 0.1 ? "suelo-chip--alerta" : ""}`}>
                    Now: {mayuscula(d.ultimo.clase)} (NDVI {d.ultimo.ndvi})
                  </span>
                )}
                <GraficaMeses meses={d.promedio_por_mes} />
                <p className="suelo-nota">
                  {d.meses_suelo_desnudo.length
                    ? `Months with bare soil (NDVI ≤ 0.1): ${d.meses_suelo_desnudo.map(mesCompleto).join(", ")}.`
                    : "No month reaches bare soil (NDVI ≤ 0.1)."}{" "}
                  {d.mes_menor_cobertura &&
                    `Lowest cover in ${mesCompleto(d.mes_menor_cobertura.mes)} (NDVI ${d.mes_menor_cobertura.ndvi_promedio}). `}
                  Average {d.anios_promediados}.
                </p>
                <Fuente>MODIS MOD13Q1 (NDVI) · USGS classes</Fuente>
              </Tarjeta>
            )}
          </Cargable>

          <div className="suelo__ancho">
            <Cargable estado={retencion} alto={240}>
              {(d) => (
                <Tarjeta>
                  <EncabezadoTarjeta etiqueta="Last weeks" titulo="How your soil holds water" />
                  <Ayuda termino="retencion" />
                  <GraficaRetencion dias={d.dias} />
                  <p className="suelo-nota">
                    When it rains, moisture goes up; if it drops fast, the soil holds little water. {d.nota}
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
                  <EncabezadoTarjeta etiqueta="SoilGrids · 250 m" titulo="Soil properties" />
                  <Ayuda termino="propiedades" />
                  {d.sin_datos ? (
                    <p className="suelo-nota">{d.aviso}</p>
                  ) : (
                    <div className="suelo-tabla">
                      <table>
                        <thead>
                          <tr>
                            <th>Depth</th>
                            <th>pH</th>
                            <th>Texture</th>
                            <th>Clay</th>
                            <th>Sand</th>
                            <th>Silt</th>
                            <th>Organic carbon</th>
                            <th>Organic matter (estimated)</th>
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
                    SoilGrids (ISRIC) · texture: USDA triangle · organic matter = carbon × 1.724 (Van Bemmelen,
                    NOM-021-SEMARNAT-2000)
                  </Fuente>
                </Tarjeta>
              )}
            </Cargable>
          </div>

          <Cargable estado={erosion} alto={220}>
            {(d) => (
              <Tarjeta>
                <EncabezadoTarjeta etiqueta="NASA SRTM · 30 m" titulo="Land and erosion" />
                <Ayuda termino="erosion" />
                <span className="suelo-chip suelo-chip--neutro">{mayuscula(d.clase_pendiente_fao)}</span>
                <div className="suelo-datos">
                  <Dato etiqueta="Average slope" valor={d.terreno.pendiente_promedio_pct} unidad="%" />
                  <Dato etiqueta="Maximum slope" valor={d.terreno.pendiente_maxima_pct} unidad="%" />
                  <Dato etiqueta="Elevation" valor={d.terreno.elevacion_m} unidad="m" />
                  <Dato etiqueta={`Days/year with rain ≥${d.lluvias_fuertes.umbral_mm} mm`} valor={d.lluvias_fuertes.dias_por_anio} />
                  <Dato etiqueta="Max. rain in one day" valor={d.lluvias_fuertes.lluvia_maxima_dia_mm} unidad="mm" />
                  <Dato etiqueta="LS factor (RUSLE)" valor={d.factor_ls.ls_promedio} />
                  <Dato etiqueta="Max. LS factor" valor={d.factor_ls.ls_maximo} />
                </div>
                <p className="suelo-nota">
                  LS factor: how much the shape of the land increases soil loss. {d.factor_ls.referencia}; an LS of 2 means
                  twice the loss, all else being equal.
                </p>
                <p className="suelo-nota">
                  Slope within ~{d.terreno.area_analizada_m} m of the point · rain {d.lluvias_fuertes.periodo}
                </p>
                <Fuente>NASA SRTM + NASA POWER · FAO slope classes · R20mm index (WMO) · RUSLE LS factor (Moore & Burch, 1986)</Fuente>
              </Tarjeta>
            )}
          </Cargable>

          <Cargable estado={agua} alto={220}>
            {(d) => (
              <Tarjeta>
                <EncabezadoTarjeta etiqueta="NASA GRACE / GRACE-FO" titulo="Water stored in the region" />
                <Ayuda termino="grace" />
                <span className={`suelo-chip ${d.tendencia_cm_por_anio < 0 ? "suelo-chip--alerta" : ""}`}>
                  {d.lectura}: {d.tendencia_cm_por_anio} cm/year
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
                  <EncabezadoTarjeta etiqueta="Trend" titulo={`Root-zone moisture ${ANIO_INICIO}–${ANIO_FIN}`} />
                  <GraficaLinea puntos={d.serie.map((p) => ({ x: fechaPower(p.fecha), y: p.humedad_raiz }))} unidad="%" />
                  <Fuente>NASA POWER (monthly)</Fuente>
                </Tarjeta>
              )}
            </Cargable>
          </div>
        </>
      )}

      <p className="suelo-nota suelo__ancho">
        Soil data for {nombre} comes from the nearest cropland point (NASA MODIS land cover), not the city itself. NASA
        POWER (~50 km), SMAP (9 km) and GRACE (~300 km) describe the region, not your exact field.
      </p>
    </div>
  );
}
