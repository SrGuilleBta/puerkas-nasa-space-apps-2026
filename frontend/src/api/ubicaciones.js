// Ubicaciones guardadas: los lugares para los que se consulta el clima y el suelo.
// El backend trae 4 ciudades de inicio; se pueden agregar más, quitar, y guardar "Mi ubicación".
import { enviar, obtener } from "./cliente.js";

const R = "/api/ubicaciones";

export const listarUbicaciones = () => obtener(R);

// Busca lugares por nombre para poder agregarlos. No guarda nada. -> [{ nombre, lat, lon, zona }]
export const buscarLugares = (texto) => obtener(`${R}/buscar`, { q: texto });

// datos = { nombre, lat, lon, zona }
export const crearUbicacion = (datos) => enviar("POST", R, datos);

// Guarda (o actualiza) "Mi ubicación". datos = { lat, lon, zona }
export const guardarMiUbicacion = (datos) => enviar("PUT", `${R}/mi-ubicacion`, datos);

export const borrarUbicacion = (id) => enviar("DELETE", `${R}/${id}`);
