"""Pipeline de Cultivos.

Uso (desde backend/):
    python -m pipeline.cultivos descargar   # baja Monitor de Sequía, EcoCrop e inflación
    python -m pipeline.cultivos             # calcula indicadores y escribe data/cultivos/
"""

import sys
import time

from . import catalogo, config, descargas, exportar, fuentes, indicadores, rotacion


def construir():
    t0 = time.time()
    paso = lambda msg: print(f"[{time.time() - t0:5.1f}s] {msg}")

    paso("Cargando SIAP")
    agg, crudo = fuentes.cargar_siap()
    estados, municipios, nombres_cult = fuentes.nombres(crudo)
    desde, hasta = indicadores.ventana(agg)
    agg = agg[agg["anio"] >= desde]
    paso(f"  {len(agg):,} filas en la ventana {desde}-{hasta}")

    paso("Cargando Monitor de Sequía, EcoCrop, inflación y curado")
    seq, nombres_seq = fuentes.cargar_sequia()
    eco = fuentes.cargar_ecocrop()
    deflactor = fuentes.cargar_deflactor()
    curado = fuentes.cargar_curado()

    paso("Temporadas con sequía severa por ubicación")
    flags = indicadores.temporadas_sequia(seq, range(desde, hasta + 1))
    ctx = indicadores.contexto_sequia(seq, hasta)

    paso("Indicadores por municipio, estado y nación")
    niveles = indicadores.por_nivel(agg)
    por_combo, por_cult = indicadores.calcular(niveles, flags, deflactor)
    por_combo = por_combo[por_combo["n_anios"] > 0]
    por_cult = por_cult[por_cult["n_anios"] > 0]

    nac = por_cult[por_cult["nivel"] == "nacional"].copy()
    n_mun = por_cult[por_cult["nivel"] == "municipio"].groupby("cultivo_id").size()
    nac["n_municipios"] = nac["cultivo_id"].map(n_mun).fillna(0)

    paso("Catálogo")
    cat, rasgos = catalogo.construir(nombres_cult, curado, eco, nac)

    paso("Rotación practicada")
    co = rotacion.coocurrencia(agg, desde)
    rot = rotacion.puntuar(co, rasgos, nombres_cult["nombre"].to_dict())

    paso("Escribiendo JSON")
    fuentes_meta = {
        "siap": f"Cierre de la Producción Agrícola {desde}-{hasta}",
        "sequia": f"Monitor de Sequía de México (CONAGUA/SMN), corte {ctx['fecha_actual'].iloc[0]}",
        "ecocrop": "FAO EcoCrop (tabla OpenCLIM/ecocrop)",
        "inflacion": "FMI WEO, inflación promedio anual de México (PCPIPCH)",
        "gaez": "pendiente",
        "cenapred": "pendiente",
    }
    n = exportar.exportar(cat, por_cult, por_combo, rot, ctx, (estados, municipios),
                          desde, hasta, fuentes_meta)
    con_datos = set(por_cult.loc[por_cult["nivel"] == "municipio", "clave"])
    exportar.exportar_ubicaciones(estados, municipios, nombres_seq, con_datos)
    paso(f"Listo: {len(cat)} cultivos en catálogo, {n} archivos de ubicación en {config.SALIDA_DIR}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "descargar":
        descargas.descargar_todo()
    else:
        construir()
