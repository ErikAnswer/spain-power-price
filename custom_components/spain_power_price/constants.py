"""Constants for the Spain Power Price integration."""

DOMAIN = "spain_power_price"
PLATFORMS = ["sensor"]

CONF_PERSONAL_TOKEN = "token_personal"

HEADER_ACCEPT = "application/json; application/vnd.esios-api-v1+json"
HEADER_CONTENT_TYPE = "application/json"
HEADER_API_KEY = "x-api-key"

ENDPOINT_FUTURE_PRICE = "https://api.esios.ree.es/archives/70/download_json?locale=es"
ENDPOINT_TODAY_PRICE = (
    "https://api.esios.ree.es/archives/70/download_json?locale=es&date={}"
)

FIELD_DAY = "Dia"
FIELD_HOUR = "Hora"
FIELD_PCB = "PCB"
FIELD_CYM = "CYM"
