# Spain Power Price

Integration for [Home Assistant](https://www.home-assistant.io/) that provides Spain electricity hourly pricing from [ESIOS](https://www.esios.ree.es/).
<br><br>

## Features

This integration includes:

- Current electricity price.
- Price date sensor.
  <br>

## Requirements

- A working [Home Assistant](https://www.home-assistant.io/) installation.
- [HACS](https://hacs.xyz/) installed in Home Assistant.
- A personal ESIOS API token (request via [consultasios@ree.es](mailto:consultasios@ree.es)).
  <br>

## Installation

### Recommended: HACS

1. Add this repository as a custom repository in HACS (category: **Integration**):

- `https://github.com/ErikAnswer/spain-power-price`

2. Open the repository directly in your Home Assistant:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ErikAnswer&repository=spain-power-price&category=integration)

3. Click **Download** in HACS.
4. Restart Home Assistant.
5. Add the integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=spain-power-price)

6. Enter your ESIOS token and finish setup.

### Manual

1. Copy `custom_components/spain-power-price` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **Spain Power Price** and enter your ESIOS token.

## Configuration

- Configuration is UI-only (config entry).

## ESIOS API

- Uses `x-api-key` authentication header with JSON accept/content-type.
- Uses PVPC archive endpoint: `archives/70/download_json`.

## Sensors

- **Spain Power Price - PVPC - Current**
- **Spain Power Price - PVPC - Date**

**Note:** ESIOS usually publishes next-day prices from around 20:30.

Extra attributes include:

- `id`
- `integration`
- `relativePrice` (`0` low, `1` medium, `2` high)
- `dayPrices` list with `id`, `day`, `hour`, `pcb`, `pcbRelative`, `cym`, `cymRelative`
