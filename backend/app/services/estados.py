"""Estados de México (clave INEGI de 2 dígitos), para ligar cada ubicación con las agendas del INIFAP."""

from app.db import clave

ESTADOS = {
    "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur", "04": "Campeche",
    "05": "Coahuila", "06": "Colima", "07": "Chiapas", "08": "Chihuahua", "09": "Ciudad de México",
    "10": "Durango", "11": "Guanajuato", "12": "Guerrero", "13": "Hidalgo", "14": "Jalisco",
    "15": "México", "16": "Michoacán", "17": "Morelos", "18": "Nayarit", "19": "Nuevo León",
    "20": "Oaxaca", "21": "Puebla", "22": "Querétaro", "23": "Quintana Roo", "24": "San Luis Potosí",
    "25": "Sinaloa", "26": "Sonora", "27": "Tabasco", "28": "Tamaulipas", "29": "Tlaxcala",
    "30": "Veracruz", "31": "Yucatán", "32": "Zacatecas",
}

# Nombres con los que el buscador de lugares puede devolver un estado y que no coinciden con el de INEGI
ALIAS = {
    "estado de mexico": "15", "state of mexico": "15", "mexico state": "15", "edomex": "15",
    "mexico city": "09", "ciudad de mexico": "09", "federal district": "09", "distrito federal": "09", "cdmx": "09",
}


def listar() -> list[dict]:
    return sorted(({"clave": k, "nombre": v} for k, v in ESTADOS.items()), key=lambda e: clave(e["nombre"]))


def estado_de(nombre: str | None) -> str | None:
    """Clave del estado a partir de su nombre ("Nuevo León", "Coahuila de Zaragoza", "State of Mexico")."""
    if not nombre:
        return None
    n = clave(nombre)
    if n in ALIAS:
        return ALIAS[n]
    for cve, oficial in ESTADOS.items():
        o = clave(oficial)
        if n == o or (len(o) > 4 and n.startswith(o + " ")):  # "Coahuila de Zaragoza", "Veracruz de Ignacio..."
            return cve
    return None
