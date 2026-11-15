// Estimaciones para las tarjetas técnicas de Suelo, a partir de la proyección del backend (/api/suelo/proyeccion,
// ver backend/app/services/suelo/proyeccion.py). Todo lo que sale de aquí es una estimación, no una medición.

// Retención: la lluvia que POWER aún no trae (los últimos 2-3 días) se llena con la que Open-Meteo ya registró, y se
// suman las barras de la lluvia pronosticada. Cada barra estimada lleva `estimada: true` para dibujarla distinta.
export function lluviaConPronostico(dias, p) {
  if (!p || dias.length === 0) return { dias, proximos: [] };
  const mm = Object.fromEntries(p.proyeccion.map((r) => [r.fecha, r.lluvia_mm]));
  const ultima = dias[dias.length - 1].fecha;
  return {
    dias: dias.map((d) => (d.lluvia_mm == null && mm[d.fecha] != null ? { ...d, lluvia_mm: mm[d.fecha], estimada: true } : d)),
    proximos: p.proyeccion.filter((r) => r.fecha > ultima).map((r) => ({ fecha: r.fecha, mm: r.lluvia_mm ?? 0 })),
  };
}

// Humedad de la raíz de SMAP L4 (% de volumen): al último valor se le aplica el mismo cambio de agua que el balance
// calculó. Un milímetro de agua en 1 000 mm de suelo es 0.1 punto de volumen, así que el cambio en mm se divide entre 10.
// Devuelve [{fecha, y}] de los días después del último dato de SMAP, o [] si no se puede.
export function estimarRaizSmap(serie, p) {
  const validos = serie.filter((m) => m.raiz_pct_volumen != null);
  if (!p || validos.length === 0) return [];
  const ultimo = validos[validos.length - 1];
  const almacen = p.supuestos.almacen_mm;
  const mm = Object.fromEntries([...p.real, ...p.proyeccion].map((r) => [r.fecha, (r.humedad_raiz / 100) * almacen]));
  const base = mm[ultimo.fecha];
  if (base == null) return [];
  return p.proyeccion
    .filter((r) => r.fecha > ultimo.fecha)
    .map((r) => ({ fecha: r.fecha, y: Math.max(0, Math.round((ultimo.raiz_pct_volumen + (mm[r.fecha] - base) / 10) * 10) / 10) }));
}

// ---- Agua subterránea (GRACE): la tendencia prolongada, no un pronóstico ----

const anioDecimal = (iso) => {
  const f = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return f.getFullYear() + (f.getMonth() + f.getDate() / 31) / 12;
};

// Pendiente (cm por año) de una regresión lineal por mínimos cuadrados
function pendiente(puntos) {
  const n = puntos.length;
  if (n < 3) return null;
  const mx = puntos.reduce((s, p) => s + p.x, 0) / n;
  const my = puntos.reduce((s, p) => s + p.y, 0) / n;
  const den = puntos.reduce((s, p) => s + (p.x - mx) ** 2, 0);
  return den === 0 ? null : puntos.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0) / den;
}

// Prolonga la serie de GRACE con el ritmo de la tendencia de toda la serie (la que ya muestra la tarjeta), partiendo del
// último dato. También da el ritmo de los últimos 5 años, porque el promedio de 24 años puede quedarse corto o largo.
// "Si sigue así": no es un pronóstico, el agua subterránea depende de las lluvias y del bombeo de los próximos años.
export function prolongarTendencia(serie, tendenciaPorAnio, anios = 3) {
  const validos = serie.filter((p) => p.anomalia_cm != null);
  if (validos.length < 3 || tendenciaPorAnio == null) return null;
  const ultimo = validos[validos.length - 1];
  const t0 = new Date(`${ultimo.fecha.slice(0, 10)}T12:00:00`);
  const extension = Array.from({ length: anios * 12 }, (_, k) => {
    const f = new Date(t0.getFullYear(), t0.getMonth() + k + 1, 1);
    return {
      x: `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}`,
      y: Math.round((ultimo.anomalia_cm + (tendenciaPorAnio * (k + 1)) / 12) * 10) / 10,
    };
  });
  const fin = anioDecimal(ultimo.fecha);
  const recientes = pendiente(validos.filter((p) => anioDecimal(p.fecha) >= fin - 5).map((p) => ({ x: anioDecimal(p.fecha), y: p.anomalia_cm })));
  return {
    extension,
    en5Anios: Math.round((ultimo.anomalia_cm + tendenciaPorAnio * 5) * 10) / 10,
    ultimo: ultimo.anomalia_cm,
    ritmoReciente: recientes == null ? null : Math.round(recientes * 10) / 10,
  };
}

// ---- Tendencia de humedad de raíz (20 años): lo que suele venir, no un pronóstico ----

// Para cada uno de los próximos `n` meses: promedio, mínimo y máximo de ese mes en la serie mensual de POWER
// (`serie` trae fecha "AAAAMM" y humedad_raiz). Es la climatología del lugar: lo típico, no lo que pasará este año.
export function tipicoProximosMeses(serie, mesActual, n = 6) {
  const porMes = Array.from({ length: 12 }, () => []);
  for (const p of serie) {
    if (p.humedad_raiz != null) porMes[Number(p.fecha.slice(4, 6)) - 1].push(p.humedad_raiz);
  }
  const anios = new Set(serie.map((p) => p.fecha.slice(0, 4))).size;
  const meses = Array.from({ length: n }, (_, k) => {
    const mes = (mesActual + k + 1) % 12; // 0 = enero
    const v = porMes[mes];
    if (v.length === 0) return null;
    return {
      mes,
      promedio: Math.round((v.reduce((s, x) => s + x, 0) / v.length) * 10) / 10,
      min: Math.min(...v),
      max: Math.max(...v),
    };
  });
  return meses.every(Boolean) ? { meses, anios } : null;
}
