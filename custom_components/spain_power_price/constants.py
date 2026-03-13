"""Constants for the Spain Power Price integration."""

DOMAIN = "spain_power_price"
PLATFORMS = ["sensor"]

CONF_PERSONAL_TOKEN = "token_personal"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

DEFAULT_UPDATE_INTERVAL_MINUTES = 30
MIN_UPDATE_INTERVAL_MINUTES = 5
MAX_UPDATE_INTERVAL_MINUTES = 120

HEADER_ACCEPT = "application/json; application/vnd.esios-api-v1+json"
HEADER_CONTENT_TYPE = "application/json"
HEADER_API_KEY = "x-api-key"

ENDPOINT_FUTURE_PRICE = "https://api.esios.ree.es/archives/70/download_json?locale=es"
ENDPOINT_TODAY_PRICE = (
    "https://api.esios.ree.es/archives/70/download_json?locale=es&date={}"
)
ENDPOINT_INDICATOR_RANGE = (
    "https://api.esios.ree.es/indicators/{indicator_id}?start_date={start_date}"
    "&end_date={end_date}&time_trunc=hour"
)

INDICATOR_SPOT_PRICE_DAILY = 600
INDICATOR_DEMAND_FORECAST = 460
INDICATOR_DEMAND_PROGRAMMED = 545
INDICATOR_WIND_FORECAST = 541
INDICATOR_SOLAR_FORECAST = 542
INDICATOR_WIND_REAL = 551

FIELD_DAY = "Dia"
FIELD_HOUR = "Hora"
FIELD_PCB = "PCB"
FIELD_CYM = "CYM"
