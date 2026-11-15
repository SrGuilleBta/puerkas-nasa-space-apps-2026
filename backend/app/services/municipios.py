from dataclasses import dataclass

# El agricultor elige su ESTADO en el selector de arriba; los datos son por estado (a nivel
# municipio no siempre hay datos). Se conserva el nombre "Municipio"/"MUNICIPIOS" para no cambiar el
# código que ya lo usa.


@dataclass(frozen=True)
class Municipio:
    nombre: str  # igual que en el selector del frontend (components/Layout.jsx)
    lat: float  # capital del estado: punto para el clima
    lon: float
    zona: str  # zona horaria IANA
    # Punto de campo para consultar el suelo: el píxel de CULTIVO más cercano a la capital según el
    # mapa de cobertura de NASA MODIS (MCD12Q1, clases IGBP 12/14), con scripts/buscar_cultivo.py.
    # Excepción: CDMX, donde el más cercano caía en el Estado de México; se usa cultivo en Tláhuac.
    lat_suelo: float
    lon_suelo: float


MUNICIPIOS = [
    Municipio("Aguascalientes", 21.8853, -102.2916, "America/Mexico_City", 21.9062, -102.3191),  # cultivo MODIS a ~3 km de la capital
    Municipio("Baja California", 32.6245, -115.4523, "America/Tijuana", 32.6646, -115.5325),  # cultivo MODIS a ~5 km de la capital
    Municipio("Baja California Sur", 24.1426, -110.3128, "America/Mazatlan", 23.7396, -109.8331),  # cultivo MODIS a ~47 km de la capital
    Municipio("Campeche", 19.8301, -90.5349, "America/Merida", 19.8104, -90.5217),  # cultivo MODIS a ~2 km de la capital
    Municipio("Chiapas", 16.7528, -93.1152, "America/Mexico_City", 16.7354, -93.1256),  # cultivo MODIS a ~3 km de la capital
    Municipio("Chihuahua", 28.6353, -106.0889, "America/Chihuahua", 28.6812, -105.9853),  # cultivo MODIS a ~16 km de la capital
    Municipio("Ciudad de México", 19.4326, -99.1332, "America/Mexico_City", 19.25, -98.98),  # cultivo MODIS en Tláhuac (el más cercano a la capital caía en Edomex)
    Municipio("Coahuila", 25.4232, -101.0053, "America/Monterrey", 25.4687, -100.9453),  # cultivo MODIS a ~11 km de la capital
    Municipio("Colima", 19.2433, -103.7250, "America/Mexico_City", 19.2271, -103.7253),  # cultivo MODIS a ~2 km de la capital
    Municipio("Durango", 24.0277, -104.6532, "America/Monterrey", 24.0021, -104.6193),  # cultivo MODIS a ~3 km de la capital
    Municipio("Estado de México", 19.2826, -99.6557, "America/Mexico_City", 19.3021, -99.667),  # cultivo MODIS a ~2 km de la capital
    Municipio("Guanajuato", 21.0190, -101.2574, "America/Mexico_City", 21.0062, -101.2788),  # cultivo MODIS a ~4 km de la capital
    Municipio("Guerrero", 17.5506, -99.5050, "America/Mexico_City", 17.5479, -99.5164),  # cultivo MODIS a ~1 km de la capital
    Municipio("Hidalgo", 20.1011, -98.7591, "America/Mexico_City", 20.0771, -98.7709),  # cultivo MODIS a ~4 km de la capital
    Municipio("Jalisco", 20.6597, -103.3496, "America/Mexico_City", 20.7104, -103.4317),  # cultivo MODIS a ~8 km de la capital
    Municipio("Michoacán", 19.7060, -101.1950, "America/Mexico_City", 19.7354, -101.2183),  # cultivo MODIS a ~3 km de la capital
    Municipio("Morelos", 18.9242, -99.2216, "America/Mexico_City", 18.9062, -99.1909),  # cultivo MODIS a ~3 km de la capital
    Municipio("Nayarit", 21.5042, -104.8946, "America/Mazatlan", 21.4979, -104.8685),  # cultivo MODIS a ~2 km de la capital
    Municipio("Nuevo León", 25.6866, -100.3161, "America/Monterrey", 25.8146, -100.2801),  # cultivo MODIS a ~20 km de la capital
    Municipio("Oaxaca", 17.0732, -96.7266, "America/Mexico_City", 17.0521, -96.6728),  # cultivo MODIS a ~5 km de la capital
    Municipio("Puebla", 19.0414, -98.2063, "America/Mexico_City", 19.0896, -98.2553),  # cultivo MODIS a ~6 km de la capital
    Municipio("Querétaro", 20.5888, -100.3899, "America/Mexico_City", 20.5646, -100.3554),  # cultivo MODIS a ~3 km de la capital
    Municipio("Quintana Roo", 18.5001, -88.2961, "America/Cancun", 18.4979, -88.3105),  # cultivo MODIS a ~2 km de la capital
    Municipio("San Luis Potosí", 22.1565, -100.9855, "America/Mexico_City", 22.1312, -100.885),  # cultivo MODIS a ~9 km de la capital
    Municipio("Sinaloa", 24.8091, -107.3940, "America/Mazatlan", 24.8396, -107.428),  # cultivo MODIS a ~3 km de la capital
    Municipio("Sonora", 29.0729, -110.9559, "America/Hermosillo", 29.0771, -110.9),  # cultivo MODIS a ~6 km de la capital
    Municipio("Tabasco", 17.9892, -92.9475, "America/Mexico_City", 17.9979, -92.9723),  # mosaico de cultivo MODIS a ~2 km de la capital
    Municipio("Tamaulipas", 23.7369, -99.1411, "America/Monterrey", 23.7271, -99.1132),  # cultivo MODIS a ~2 km de la capital
    Municipio("Tlaxcala", 19.3139, -98.2404, "America/Mexico_City", 19.3146, -98.2529),  # cultivo MODIS a ~1 km de la capital
    Municipio("Veracruz", 19.5438, -96.9102, "America/Mexico_City", 19.5104, -96.8905),  # mosaico de cultivo MODIS a ~4 km de la capital
    Municipio("Yucatán", 20.9674, -89.5926, "America/Merida", 20.9396, -89.5495),  # cultivo MODIS a ~4 km de la capital
    Municipio("Zacatecas", 22.7709, -102.5832, "America/Mexico_City", 22.8187, -102.6527),  # cultivo MODIS a ~6 km de la capital
]


def buscar(nombre: str) -> Municipio | None:
    """Acepta el estado ("Nuevo León") o la opción del selector "Municipio, Estado"
    ("Apodaca, Nuevo León"): en los dos casos devuelve el ESTADO, porque los datos son por estado."""
    estado = nombre.rsplit(", ", 1)[-1].strip()
    return next((m for m in MUNICIPIOS if m.nombre == estado), None)

