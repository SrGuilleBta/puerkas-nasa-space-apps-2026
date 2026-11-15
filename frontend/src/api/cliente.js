// fetch común al backend. El frontend nunca llama a APIs externas: todo pasa por /api.
export async function obtener(ruta, parametros = {}) {
  const consulta = new URLSearchParams(parametros);
  const url = consulta.size ? `${ruta}?${consulta}` : ruta;
  const respuesta = await fetch(url);
  if (!respuesta.ok) {
    throw new Error(`No se pudo consultar ${ruta} (${respuesta.status})`);
  }
  return respuesta.json();
}
