import React, { useState, useMemo, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Search, MapPin, TrendingUp, CheckSquare, Square, Star } from 'lucide-react';
import datosAgricolas from './datos_dashboard.json';

const PALETA_COLORES = [
  '#2563eb', '#16a34a', '#dc2626', '#d97706', '#9333ea',
  '#0891b2', '#db2777', '#4f46e5', '#65a30d', '#ea580c'
];

// Formats a local Date object to 'YYYY-MM-DD' without timezone shifts
const formatearFecha = (fecha) => {
  const y = fecha.getFullYear();
  const m = String(fecha.getMonth() + 1).padStart(2, '0');
  const d = String(fecha.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

// Generates all calendar days between two dates (inclusive)
const generarCalendarioFijo = (fechaInicio, fechaFin) => {
  const fechas = [];
  const actual = new Date(fechaInicio.getFullYear(), fechaInicio.getMonth(), fechaInicio.getDate());
  const fin = new Date(fechaFin.getFullYear(), fechaFin.getMonth(), fechaFin.getDate());

  while (actual <= fin) {
    fechas.push(formatearFecha(actual));
    actual.setDate(actual.getDate() + 1);
  }
  return fechas;
};

export default function DashboardPrecios() {
  // Sort states alphabetically in English
  const estadosDisponibles = useMemo(() => {
    return Object.keys(datosAgricolas).sort((a, b) => a.localeCompare(b, 'en'));
  }, []);

  const estadoInicial = estadosDisponibles.includes('NUEVO LEON')
    ? 'NUEVO LEON'
    : (estadosDisponibles.includes('NUEVO LEÓN') ? 'NUEVO LEÓN' : estadosDisponibles[0]);

  const [estadoSeleccionado, setEstadoSeleccionado] = useState(estadoInicial);
  const [busqueda, setBusqueda] = useState('');
  const [rangoTiempo, setRangoTiempo] = useState('mes'); // 'semana', 'mes', 'anio'

  // Filters for Selected Only and Favorites Only
  const [soloSeleccionados, setSoloSeleccionados] = useState(false);
  const [soloFavoritos, setSoloFavoritos] = useState(false);

  // Favorites state persisted in localStorage
  const [favoritos, setFavoritos] = useState(() => {
    try {
      const guardados = localStorage.getItem('agro_favoritos');
      return guardados ? JSON.parse(guardados) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('agro_favoritos', JSON.stringify(favoritos));
    } catch {
      // Ignore storage errors
    }
  }, [favoritos]);

  // Sort products alphabetically by their English name (A-Z)
  const productosDelEstado = useMemo(() => {
    return Object.keys(datosAgricolas[estadoSeleccionado] || {}).sort((a, b) =>
      a.localeCompare(b, 'en')
    );
  }, [estadoSeleccionado]);

  const [productosActivos, setProductosActivos] = useState(() => {
    const prods = Object.keys(datosAgricolas[estadoInicial] || {}).sort((a, b) =>
      a.localeCompare(b, 'en')
    );
    const iniciales = prods.filter(p =>
      p.includes('TOMATO') || p.includes('LIME') || p.includes('AVOCADO') ||
      p.includes('JITOMATE') || p.includes('LIMON') || p.includes('AGUACATE')
    ).slice(0, 2);
    return iniciales.length > 0 ? iniciales : (prods[0] ? [prods[0]] : []);
  });

  const productosActivosDelEstado = useMemo(() => {
    return productosActivos.filter(prod => productosDelEstado.includes(prod));
  }, [productosActivos, productosDelEstado]);

  const favoritosDelEstadoCount = useMemo(() => {
    return favoritos.filter(prod => productosDelEstado.includes(prod)).length;
  }, [favoritos, productosDelEstado]);

  // Filter and sort: Favorites pinned at the top (A-Z), followed by remaining products (A-Z)
  const productosFiltrados = useMemo(() => {
    return productosDelEstado
      .filter(prod => {
        const coincideBusqueda = prod.toLowerCase().includes(busqueda.toLowerCase());
        const pasaSeleccionados = !soloSeleccionados || productosActivos.includes(prod);
        const pasaFavoritos = !soloFavoritos || favoritos.includes(prod);
        return coincideBusqueda && pasaSeleccionados && pasaFavoritos;
      })
      .sort((a, b) => {
        const aFav = favoritos.includes(a);
        const bFav = favoritos.includes(b);
        if (aFav && !bFav) return -1;
        if (!aFav && bFav) return 1;
        return a.localeCompare(b, 'en');
      });
  }, [productosDelEstado, busqueda, soloSeleccionados, soloFavoritos, productosActivos, favoritos]);

  const toggleProducto = (producto) => {
    setProductosActivos(prev =>
      prev.includes(producto) ? prev.filter(p => p !== producto) : [...prev, producto]
    );
  };

  const toggleFavorito = (e, producto) => {
    e.stopPropagation(); // Prevents toggling product selection when clicking the star
    setFavoritos(prev =>
      prev.includes(producto) ? prev.filter(p => p !== producto) : [...prev, producto]
    );
  };

  // BUILD CHART DATA WITH FIXED CALENDAR GRID BASED ON SYSTEM DATE
  const datosGrafica = useMemo(() => {
    const hoy = new Date();
    const anioActual = hoy.getFullYear();
    const mesActual = hoy.getMonth();

    let fechaInicio;
    let fechaFin;

    if (rangoTiempo === 'semana') {
      const diaSemana = hoy.getDay();
      fechaInicio = new Date(anioActual, mesActual, hoy.getDate() - diaSemana);
      fechaFin = new Date(fechaInicio.getFullYear(), fechaInicio.getMonth(), fechaInicio.getDate() + 7);
    } else if (rangoTiempo === 'mes') {
      fechaInicio = new Date(anioActual, mesActual, 1);
      fechaFin = new Date(anioActual, mesActual + 1, 1);
    } else {
      fechaInicio = new Date(anioActual, 0, 1);
      fechaFin = new Date(anioActual + 1, 0, 1);
    }

    const diasCalendario = generarCalendarioFijo(fechaInicio, fechaFin);
    const mapaFechas = {};
    diasCalendario.forEach(f => {
      mapaFechas[f] = { fecha: f };
    });

    const datosEstado = datosAgricolas[estadoSeleccionado] || {};
    productosActivosDelEstado.forEach(prod => {
      const serie = datosEstado[prod] || [];
      serie.forEach(punto => {
        if (mapaFechas[punto.fecha]) {
          if (punto.real !== null && punto.real !== undefined) {
            mapaFechas[punto.fecha][`${prod}_real`] = punto.real;
          }
          if (punto.proyeccion !== null && punto.proyeccion !== undefined) {
            mapaFechas[punto.fecha][`${prod}_proy`] = punto.proyeccion;
          }
        }
      });
    });

    return diasCalendario.map(f => mapaFechas[f]);
  }, [estadoSeleccionado, productosActivosDelEstado, rangoTiempo]);

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
      
      {/* HEADER & CONTROLS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp color="#16a34a" /> Agricultural Price Monitor & Forecast
          </h1>
          <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: '14px' }}>
            Average price per kilogram ($ MXN/kg) • Solid line: Historical | Dashed line: Forecast
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: '#f1f5f9', padding: '4px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            {['semana', 'mes', 'anio'].map((rango) => {
              const activo = rangoTiempo === rango;
              const etiquetas = { semana: 'Week', mes: 'Month', anio: 'Year' };
              return (
                <button
                  key={rango}
                  onClick={() => setRangoTiempo(rango)}
                  style={{
                    background: activo ? '#ffffff' : 'transparent',
                    border: 'none',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontWeight: '600',
                    fontSize: '13px',
                    cursor: 'pointer',
                    boxShadow: activo ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                    color: activo ? '#0f172a' : '#64748b'
                  }}
                >
                  {etiquetas[rango]}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#f8fafc', padding: '8px 14px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            <MapPin size={18} color="#2563eb" />
            <label htmlFor="estado-select" style={{ fontWeight: '600', fontSize: '14px' }}>State:</label>
            <select
              id="estado-select"
              value={estadoSeleccionado}
              onChange={(e) => setEstadoSeleccionado(e.target.value)}
              style={{ border: 'none', background: 'transparent', fontSize: '15px', fontWeight: 'bold', color: '#0f172a', cursor: 'pointer', outline: 'none' }}
            >
              {estadosDisponibles.map(est => (
                <option key={est} value={est}>{est}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* MAIN WORKSPACE: CHART ON THE LEFT + SEARCH & PRODUCT MENU ON THE RIGHT */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) 350px',
        gap: '20px',
        alignItems: 'stretch'
      }}>

        {/* LEFT COLUMN: COMPACT CHART CONTAINER */}
        <div style={{
          background: '#ffffff',
          padding: '20px',
          borderRadius: '12px',
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
          border: '1px solid #e2e8f0',
          height: '500px',
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0
        }}>
          {productosActivosDelEstado.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
              Select at least one product from the right panel to display the chart.
            </div>
          ) : (
            <div style={{ width: '100%', flex: 1, minHeight: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={datosGrafica} margin={{ top: 10, right: 20, left: 5, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="fecha" tick={{ fontSize: 12 }} minTickGap={25} />
                  <YAxis tickFormatter={(val) => `$${val}`} tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                  <Tooltip
                    formatter={(value, name) => {
                      const esProy = name.endsWith('_proy');
                      const nombreLimpio = name.replace('_real', '').replace('_proy', '');
                      return [`$${Number(value).toFixed(2)} / kg`, `${nombreLimpio} ${esProy ? '(Forecast)' : '(Actual)'}`];
                    }}
                  />
                  {/* Clean single-icon legend */}
                  <Legend formatter={(value) => value.replace('_real', '')} />

                  {productosActivosDelEstado.map((prod, idx) => {
                    const color = PALETA_COLORES[idx % PALETA_COLORES.length];
                    return (
                      <React.Fragment key={prod}>
                        <Line
                          type="monotone"
                          dataKey={`${prod}_real`}
                          name={prod}
                          stroke={color}
                          strokeWidth={2.5}
                          dot={false}
                          connectNulls
                        />
                        {/* legendType="none" prevents the duplicate '-o-' icon in the Legend */}
                        <Line
                          type="monotone"
                          dataKey={`${prod}_proy`}
                          name={`${prod}_proy`}
                          legendType="none"
                          stroke={color}
                          strokeWidth={2.5}
                          strokeDasharray="6 6"
                          dot={false}
                          connectNulls
                        />
                      </React.Fragment>
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* RIGHT SIDEBAR: SEARCH BAR, FILTERS & ALPHABETICAL PRODUCT MENU */}
        <div style={{
          background: '#f8fafc',
          padding: '18px',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          height: '500px',
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', gap: '6px' }}>
              <h2 style={{ fontSize: '15px', fontWeight: 'bold', margin: 0, color: '#0f172a' }}>
                Compare Products
              </h2>

              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                {/* Clickable Favorites Filter Badge */}
                <button
                  type="button"
                  onClick={() => setSoloFavoritos(prev => !prev)}
                  title="Filter by Favorites"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11.5px',
                    fontWeight: '600',
                    background: soloFavoritos ? '#fef3c7' : '#e2e8f0',
                    color: soloFavoritos ? '#b45309' : '#475569',
                    border: soloFavoritos ? '1px solid #f59e0b' : '1px solid transparent',
                    padding: '3px 8px',
                    borderRadius: '999px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <Star size={12} fill={soloFavoritos ? '#f59e0b' : 'none'} color={soloFavoritos ? '#f59e0b' : '#64748b'} />
                  {favoritosDelEstadoCount}
                </button>

                {/* Clickable Selected Filter Badge */}
                <button
                  type="button"
                  onClick={() => setSoloSeleccionados(prev => !prev)}
                  title="Click to filter only selected products"
                  style={{
                    fontSize: '11.5px',
                    fontWeight: '600',
                    background: soloSeleccionados ? '#2563eb' : '#e2e8f0',
                    color: soloSeleccionados ? '#ffffff' : '#334155',
                    border: 'none',
                    padding: '3px 9px',
                    borderRadius: '999px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {productosActivosDelEstado.length} selected
                </button>
              </div>
            </div>

            <div style={{ position: 'relative', width: '100%' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: '#64748b' }} />
              <input
                type="text"
                placeholder="Search product (A-Z)..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px 8px 36px',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  fontSize: '13px',
                  background: '#ffffff',
                  boxSizing: 'border-box',
                  outline: 'none'
                }}
              />
            </div>
          </div>

          {/* SCROLLABLE LIST (FAVORITES PINNED AT TOP, THEN A-Z) */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            paddingRight: '4px'
          }}>
            {productosFiltrados.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px', marginTop: '24px' }}>
                No matching products found.
              </div>
            ) : (
              productosFiltrados.map((prod) => {
                const indexActivo = productosActivos.indexOf(prod);
                const estaActivo = indexActivo !== -1;
                const esFavorito = favoritos.includes(prod);
                const colorAsignado = estaActivo ? PALETA_COLORES[indexActivo % PALETA_COLORES.length] : '#64748b';

                return (
                  <div
                    key={prod}
                    onClick={() => toggleProducto(prod)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '13px',
                      background: estaActivo ? '#ffffff' : (esFavorito ? '#fffbeb' : 'transparent'),
                      border: estaActivo
                        ? `1.5px solid ${colorAsignado}`
                        : (esFavorito ? '1px solid #fde68a' : '1px solid #e2e8f0'),
                      fontWeight: estaActivo ? '600' : '400',
                      transition: 'all 0.15s ease',
                      flexShrink: 0
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                      {estaActivo ? (
                        <CheckSquare size={17} color={colorAsignado} style={{ flexShrink: 0 }} />
                      ) : (
                        <Square size={17} color="#94a3b8" style={{ flexShrink: 0 }} />
                      )}
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={prod}>
                        {prod}
                      </span>
                    </div>

                    {/* Favorite Star Button */}
                    <button
                      type="button"
                      onClick={(e) => toggleFavorito(e, prod)}
                      title={esFavorito ? 'Remove from favorites' : 'Add to favorites'}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        padding: '2px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}
                    >
                      <Star
                        size={16}
                        fill={esFavorito ? '#f59e0b' : 'none'}
                        color={esFavorito ? '#f59e0b' : '#cbd5e1'}
                      />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

    </div>
  );
}