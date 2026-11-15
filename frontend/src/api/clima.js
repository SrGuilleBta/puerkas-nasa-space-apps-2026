// Mapa de Clima: pronóstico de lluvia y calor sobre México (Open-Meteo, en una malla de puntos).
import { obtener } from "./cliente.js";

// {dias, contorno, caja, paso, puntos: [{lat, lon, lluviaMm[], tmax[]}], lugares: [{nombre, lat, lon, ...}], fuente, actualizado}
export const getMapaClima = () => obtener("/api/clima/mapa");

// Condiciones de hoy en una ubicación guardada (Open-Meteo por hora + humedad del suelo de NASA POWER):
// {municipio, temperatura, sensacion, cielo, icono, humedad, vientoKmh, vientoDireccion, lluviaProbabilidad, lluviaMm,
//  temperaturaSuelo, humedadSuelo, ventana: {favorable, desde, hasta}, fuente}
export const getCondicionesLocales = (municipio) => obtener("/api/clima/local", { municipio });
