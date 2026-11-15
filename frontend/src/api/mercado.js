// Precios de Mercado (Profeco, al consumidor): estados, productos de un estado y series para la gráfica.

async function pedir(ruta, params) {
  const q = new URLSearchParams(params);
  const r = await fetch(`/api/mercado/${ruta}?${q}`);
  if (!r.ok) {
    let detalle = "";
    try {
      detalle = (await r.json()).detail || "";
    } catch {
      /* sin cuerpo JSON */
    }
    throw new Error(detalle || `Could not load the market prices (${r.status})`);
  }
  return r.json();
}

// `municipio` (la ubicación activa) sirve para sugerir el estado.
export const getEstadosMercado = (municipio) => pedir("estados", municipio ? { municipio } : {});
export const getProductosMercado = (estado) => pedir("productos", { estado });
export const getSerieMercado = (estado, productos, rango) =>
  pedir("serie", { estado, productos: productos.join(","), rango });
