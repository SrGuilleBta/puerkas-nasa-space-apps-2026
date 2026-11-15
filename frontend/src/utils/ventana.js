// Ventana de tiempo del calendario del Planificador: desde el día 1 de un mes y por N meses.
// Se puede mover (anterior/siguiente) y ampliar o reducir (zoom); no está atada a un año.
import { mesCorto } from "./fechas.js";

export const NIVELES_ZOOM = [3, 6, 12, 24, 36];
export const ZOOM_INICIAL = 12;

const mes = (anio, m) => new Date(anio, m, 1); // Date normaliza meses fuera de 0-11

// Ventana de `meses` con el día de hoy en el primer cuarto, para ver un poco de pasado.
export function ventanaInicial(meses = ZOOM_INICIAL, hoy = new Date()) {
  return { inicio: mes(hoy.getFullYear(), hoy.getMonth() - Math.floor(meses / 4)), meses };
}

export const finVentana = (v) => mes(v.inicio.getFullYear(), v.inicio.getMonth() + v.meses);

// Posición (0 a 100) de una fecha dentro de la ventana. Fuera de ella da menos de 0 o más de 100.
export const posicion = (fecha, v) => ((fecha - v.inicio) / (finVentana(v) - v.inicio)) * 100;

// Mueve la ventana medio ancho hacia atrás (-1) o hacia adelante (1).
export function mover(v, sentido) {
  const paso = Math.max(1, Math.round(v.meses / 2));
  return { ...v, inicio: mes(v.inicio.getFullYear(), v.inicio.getMonth() + sentido * paso) };
}

// Cambia el nivel de zoom (sentido +1 = ver más meses, -1 = menos) conservando el centro.
export function cambiarZoom(v, sentido) {
  const i = NIVELES_ZOOM.indexOf(v.meses);
  const nuevos = NIVELES_ZOOM[Math.min(NIVELES_ZOOM.length - 1, Math.max(0, i + sentido))];
  const desplazamiento = Math.round((v.meses - nuevos) / 2);
  return { inicio: mes(v.inicio.getFullYear(), v.inicio.getMonth() + desplazamiento), meses: nuevos };
}

// Los meses de la ventana con su posición y ancho en %, y la etiqueta según el zoom.
export function mesesDeVentana(v) {
  const total = finVentana(v) - v.inicio;
  return Array.from({ length: v.meses }, (_, i) => {
    const desde = mes(v.inicio.getFullYear(), v.inicio.getMonth() + i);
    const hasta = mes(desde.getFullYear(), desde.getMonth() + 1);
    const nombre = mesCorto(desde.getMonth()).toUpperCase();
    const cuarto = desde.getMonth() % 3 === 0;
    return {
      clave: `${desde.getFullYear()}-${desde.getMonth()}`,
      izquierda: ((desde - v.inicio) / total) * 100,
      ancho: ((hasta - desde) / total) * 100,
      // 12 meses o menos: ENE · hasta 24: E · más: solo cada trimestre
      etiqueta: v.meses <= 12 ? nombre : v.meses <= 24 ? nombre[0] : cuarto ? nombre : "",
      anio: desde.getMonth() === 0 || i === 0 ? desde.getFullYear() : null,
    };
  });
}

// Estaciones (hemisferio norte) que caen dentro de la ventana, para pintar el fondo.
const CAMBIOS = [
  [0, 1, "invierno"],
  [2, 21, "primavera"],
  [5, 21, "verano"],
  [8, 23, "otono"],
  [11, 21, "invierno"],
];

export function estaciones(v) {
  const fin = finVentana(v);
  const cortes = [];
  for (let a = v.inicio.getFullYear() - 1; a <= fin.getFullYear() + 1; a++) {
    for (const [m, d, nombre] of CAMBIOS) cortes.push({ fecha: new Date(a, m, d), nombre });
  }
  return cortes.slice(0, -1).flatMap((c, i) => {
    const desde = Math.max(c.fecha, v.inicio);
    const hasta = Math.min(cortes[i + 1].fecha, fin);
    if (hasta <= desde) return [];
    return [{ nombre: c.nombre, izquierda: posicion(new Date(desde), v), ancho: posicion(new Date(hasta), v) - posicion(new Date(desde), v) }];
  });
}
