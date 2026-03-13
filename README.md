# Spain Power Price

Home Assistant custom integration for Spain electricity data from ESIOS.

Current version: **0.9.4**

## Features

- PVPC hourly pricing (today and next day when available).
- Derived PVPC daily metrics (average/min/max, cheapest and most expensive hours).
- Additional system indicators (SPOT price, demand, wind, solar).
- Configurable refresh interval from integration options.
- Multilanguage sensor names (English and Spanish).

## Requirements

- Home Assistant installation.
- HACS (recommended) or manual custom component install.
- Personal ESIOS token (mandatory to fetch data, request at [consultasios@ree.es](mailto:consultasios@ree.es)).

## Installation

### HACS (recommended)

1. Add custom repository (category: Integration):
   - `https://github.com/ErikAnswer/spain-power-price`
2. Open in HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ErikAnswer&repository=spain-power-price&category=integration)

3. Download integration.
4. Restart Home Assistant.
5. Add integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=spain_power_price)

### Manual install

1. Copy `custom_components/spain_power_price` into your HA `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **Spain Power Price** and enter your ESIOS token.

## Configuration

Configuration is fully UI-based.

- Initial setup asks for your ESIOS token.
- Integration options include **Update interval (minutes)**.
- Allowed interval range: **5 to 120 minutes**.
- Default interval: **30 minutes**.

When options are changed, the config entry is reloaded automatically.

## Data Sources

The integration uses these ESIOS endpoints:

- PVPC archive 70 (`archives/70/download_json`)
  - Today: `...&date=YYYY-MM-DD`
  - Future: `...download_json?locale=es`
- Indicators API (`indicators/{id}` with date range and hourly truncation):
  - `600`: SPOT market daily price
  - `460`: Peninsular demand forecast
  - `545`: Programmed demand
  - `541`: Wind forecast
  - `542`: Solar photovoltaic forecast
  - `551`: Real wind generation

## Sensors

### PVPC sensors

- PVPC current price
- PVPC next day
- PVPC average price
- PVPC minimum price
- PVPC maximum price
- PVPC cheapest hour
- PVPC most expensive hour
- PVPC top 3 cheapest hours
- PVPC top 3 most expensive hours

### Indicator sensors

- SPOT market price
- Demand forecast
- Programmed demand
- Wind forecast
- Solar forecast
- Wind real generation

## Attributes

All sensors include at least:

- `id`
- `integration`

Additional attributes by sensor type:

- `current_price`: `relativePrice`, `dayPrices`
- `future_day`: `relativePrice`, `dayPrices`
- `pvpc_*`: `dayPrices`
- indicator sensors: `indicator_id`, `indicator_name`, `geo_name`, `geo_id`, `datetime`

`dayPrices` entries include: `id`, `day`, `hour`, `pcb`, `pcbRelative`, `cym`, `cymRelative`.

## Refresh Behavior

- Uses `DataUpdateCoordinator` polling.
- First refresh is executed on setup (`first_refresh`).
- Each HTTP request has a 15s timeout.
- Endpoint failures are handled gracefully:
  - if previous data exists, last known data is preserved;
  - otherwise safe empty data is returned.
