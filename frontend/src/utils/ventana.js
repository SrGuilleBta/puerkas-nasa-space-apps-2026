// Ventana de tiempo del calendario del Planificador: desde un instante y por N meses.
// Se puede desplazar de forma continua (arrastrar, rueda, teclado), mover por bloques y ampliar
// o reducir (zoom). No está atada a un año ni a límites de mes.
import { deISO, mesCorto } from "./fechas.js";

export const NIVELES_ZOOM = [3, 6, 12, 24, 36];
export const ZOOM_INICIAL = 12;

const DIA_MS = 86400000;
const DIAS_POR_MES = 30.4375;
const LIMITE_DIAS = 3650; // no alejarse más de ~10 años de hoy (para no perderse)

const mes = (anio, m) => new Date(anio, m, 1); // Date normaliza meses fuera de 0-11

// Cuánto dura la ventana, en milisegundos. Es fija para un nivel de zoom, así que el ancho de un
// mes no "salta" mientras se desplaza.
const duracion = (meses) => Math.round(meses * DIAS_POR_MES) * DIA_MS;

// Mantiene la ventana dentro de ~10 años alrededor de hoy.
function acotar(inicioMs, meses) {
  const hoy = Date.now();
  const minimo = hoy - LIMITE_DIAS * DIA_MS;
  const maximo = hoy + LIMITE_DIAS * DIA_MS - duracion(meses);
  return new Date(Math.min(maximo, Math.max(minimo, inicioMs)));
}

// Ventana de `meses` que empieza el día 1 de un mes, con hoy en el primer cuarto (se ve algo de pasado).
export function ventanaInicial(meses = ZOOM_INICIAL, hoy = new Date()) {
  return { inicio: mes(hoy.getFullYear(), hoy.getMonth() - Math.floor(meses / 4)), meses };
}

export const finVentana = (v) => new Date(v.inicio.getTime() + duracion(v.meses));

// Posición (0 a 100) de una fecha dentro de la ventana. Fuera de ella da menos de 0 o más de 100.
export const posicion = (fecha, v) => ((fecha - v.inicio) / (finVentana(v) - v.inicio)) * 100;

// Desplaza la ventana una fracción de su ancho (positivo = hacia el futuro, negativo = hacia el pasado).
export function desplazar(v, fraccion) {
  return { ...v, inicio: acotar(v.inicio.getTime() + fraccion * duracion(v.meses), v.meses) };
}

// Mueve la ventana medio ancho hacia atrás (-1) o hacia adelante (1).
export const mover = (v, sentido) => desplazar(v, sentido * 0.5);

// Cambia el nivel de zoom (sentido +1 = ver más meses, -1 = menos) conservando el centro.
export function cambiarZoom(v, sentido) {
  const i = NIVELES_ZOOM.indexOf(v.meses);
  const nuevos = NIVELES_ZOOM[Math.min(NIVELES_ZOOM.length - 1, Math.max(0, i + sentido))];
  const centro = v.inicio.getTime() + duracion(v.meses) / 2;
  return { inicio: acotar(centro - duracion(nuevos) / 2, nuevos), meses: nuevos };
}

// Los meses que tocan la ventana, con su posición y ancho en %. Como la ventana puede empezar a
// mitad de mes, el primero y el último pueden quedar cortados.
//  - `visible`: el centro del mes está dentro; solo esos llevan etiqueta.
//  - `etiqueta`: ENE (hasta 12 meses) · E (hasta 24) · solo cada trimestre (más).
//  - `anio`: se muestra en enero y en la primera etiqueta visible.
export function mesesDeVentana(v) {
  const fin = finVentana(v);
  const total = fin - v.inicio;
  const resultado = [];
  let hayPrimeraVisible = false;
  for (let desde = mes(v.inicio.getFullYear(), v.inicio.getMonth()); desde < fin; desde = mes(desde.getFullYear(), desde.getMonth() + 1)) {
    const hasta = mes(desde.getFullYear(), desde.getMonth() + 1);
    const izquierda = ((desde - v.inicio) / total) * 100;
    const ancho = ((hasta - desde) / total) * 100;
    const centro = izquierda + ancho / 2;
    const nombre = mesCorto(desde.getMonth()).toUpperCase();
    const etiqueta = v.meses <= 12 ? nombre : v.meses <= 24 ? nombre[0] : desde.getMonth() % 3 === 0 ? nombre : "";
    const visible = centro > 0 && centro < 100;
    const anio = visible && (desde.getMonth() === 0 || !hayPrimeraVisible) ? desde.getFullYear() : null;
    if (visible) hayPrimeraVisible = true;
    resultado.push({ clave: `${desde.getFullYear()}-${desde.getMonth()}`, izquierda, ancho, etiqueta, visible, anio });
  }
  return resultado;
}

// Lleva la ventana a empezar en `inicio` (la usa la barra de desplazamiento).
export const moverA = (v, inicio) => ({ ...v, inicio: acotar(inicio.getTime(), v.meses) });

// Todo el tramo que cubre la barra de desplazamiento: desde un año antes de la primera fecha del
// plan (o de hoy) hasta un año después de la última. Así siempre hay espacio para moverse.
export function rangoDelPlan(plan, hoy = new Date()) {
  const fechas = plan.parcelas.flatMap((p) => p.siembras.flatMap((s) => [deISO(s.fechaSiembra), deISO(s.fechaCosecha)]));
  const todas = [hoy, ...fechas];
  const primera = new Date(Math.min(...todas));
  const ultima = new Date(Math.max(...todas));
  return { inicio: mes(primera.getFullYear(), primera.getMonth() - 12), fin: mes(ultima.getFullYear(), ultima.getMonth() + 13) };
}
