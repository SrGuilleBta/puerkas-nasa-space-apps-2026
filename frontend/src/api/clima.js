// Mapa de Clima: pronóstico de lluvia y calor sobre México (Open-Meteo, en una malla de puntos).
import { obtener } from "./cliente.js";

// {dias, contorno, caja, paso, puntos: [{lat, lon, lluviaMm[], tmax[]}], lugares: [{nombre, lat, lon, ...}], fuente, actualizado}
export const getMapaClima = () => obtener("/api/clima/mapa");
