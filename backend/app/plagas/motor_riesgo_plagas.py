import requests
from requests.auth import HTTPBasicAuth

# 1. Configuración de EPPO API v2
EPPO_API_KEY = "575975242e06415e9d70269f24c4df10"
EPPO_BASE_URL = "https://data.eppo.int/api/v2"

# Encabezados estándar para EPPO v2
EPPO_HEADERS = {
    "X-Api-Key": EPPO_API_KEY,
    "Accept": "application/json"
}

# 2. Configuración de Meteomatics
METEO_USER = "hackathon_nasa_space_apps_esquivel_eder"
METEO_PASS = "52aV0CsnXHf4GwfRj3Lc"
METEO_BASE_URL = "https://api.meteomatics.com"