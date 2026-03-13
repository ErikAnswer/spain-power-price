"""Spain Power Price sensors (modern architecture)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import constants
from .coordinator import SpainPowerPriceCoordinator


@dataclass(frozen=True)
class SpainPowerPriceSensorDescription(SensorEntityDescription):
    """Spain Power Price sensor description."""

    key: str
    icon: str = "mdi:flash"


SENSOR_DESCRIPTIONS = (
    SpainPowerPriceSensorDescription(
        key="current_price",
        translation_key="current_price",
        icon="mdi:currency-eur",
        native_unit_of_measurement="€/kWh",
    ),
    SpainPowerPriceSensorDescription(
        key="future_day",
        translation_key="future_day",
        icon="mdi:calendar",
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_average_price",
        translation_key="pvpc_average_price",
        icon="mdi:chart-line",
        native_unit_of_measurement=CURRENCY_EURO,
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_min_price",
        translation_key="pvpc_min_price",
        icon="mdi:arrow-down-bold",
        native_unit_of_measurement=CURRENCY_EURO,
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_max_price",
        translation_key="pvpc_max_price",
        icon="mdi:arrow-up-bold",
        native_unit_of_measurement=CURRENCY_EURO,
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_cheapest_hour",
        translation_key="pvpc_cheapest_hour",
        icon="mdi:clock-outline",
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_most_expensive_hour",
        translation_key="pvpc_most_expensive_hour",
        icon="mdi:clock-alert-outline",
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_cheapest_hours_top3",
        translation_key="pvpc_cheapest_hours_top3",
        icon="mdi:format-list-numbered",
    ),
    SpainPowerPriceSensorDescription(
        key="pvpc_most_expensive_hours_top3",
        translation_key="pvpc_most_expensive_hours_top3",
        icon="mdi:format-list-numbered",
    ),
    SpainPowerPriceSensorDescription(
        key="spot_price_daily",
        translation_key="spot_price_daily",
        icon="mdi:finance",
        native_unit_of_measurement=CURRENCY_EURO,
    ),
    SpainPowerPriceSensorDescription(
        key="demand_forecast",
        translation_key="demand_forecast",
        icon="mdi:flash-outline",
        native_unit_of_measurement=UnitOfPower.MEGA_WATT,
    ),
    SpainPowerPriceSensorDescription(
        key="demand_programmed",
        translation_key="demand_programmed",
        icon="mdi:transmission-tower",
        native_unit_of_measurement=UnitOfPower.MEGA_WATT,
    ),
    SpainPowerPriceSensorDescription(
        key="wind_forecast",
        translation_key="wind_forecast",
        icon="mdi:weather-windy",
        native_unit_of_measurement=UnitOfPower.MEGA_WATT,
    ),
    SpainPowerPriceSensorDescription(
        key="solar_forecast",
        translation_key="solar_forecast",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UnitOfPower.MEGA_WATT,
    ),
    SpainPowerPriceSensorDescription(
        key="wind_real",
        translation_key="wind_real",
        icon="mdi:wind-power",
        native_unit_of_measurement=UnitOfPower.MEGA_WATT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from a config entry."""
    personal_token = entry.data[constants.CONF_PERSONAL_TOKEN]

    raw_interval = entry.options.get(
        constants.CONF_UPDATE_INTERVAL_MINUTES,
        constants.DEFAULT_UPDATE_INTERVAL_MINUTES,
    )
    try:
        update_interval_minutes = int(raw_interval)
    except (TypeError, ValueError):
        update_interval_minutes = constants.DEFAULT_UPDATE_INTERVAL_MINUTES

    update_interval_minutes = max(
        constants.MIN_UPDATE_INTERVAL_MINUTES,
        min(constants.MAX_UPDATE_INTERVAL_MINUTES, update_interval_minutes),
    )

    coordinator = SpainPowerPriceCoordinator(
        hass,
        personal_token,
        update_interval=timedelta(minutes=update_interval_minutes),
    )
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [SpainPowerPriceSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    )


class SpainPowerPriceSensor(CoordinatorEntity[SpainPowerPriceCoordinator], SensorEntity):
    """Sensor entity for Spain Power Price data."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: SpainPowerPriceCoordinator,
        description: SpainPowerPriceSensorDescription,
    ) -> None:
        """Initialize sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{constants.DOMAIN}_{description.key}"

    @property
    def native_value(self) -> str | float | None:
        """Return native sensor value."""
        data = self.coordinator.data
        key = self.entity_description.key
        value_map: dict[str, str] = {
            "current_price": "current_price",
            "future_day": "future_day",
            "pvpc_average_price": "pvpc_average_price",
            "pvpc_min_price": "pvpc_min_price",
            "pvpc_max_price": "pvpc_max_price",
            "pvpc_cheapest_hour": "pvpc_cheapest_hour",
            "pvpc_most_expensive_hour": "pvpc_most_expensive_hour",
            "pvpc_cheapest_hours_top3": "pvpc_cheapest_hours_top3",
            "pvpc_most_expensive_hours_top3": "pvpc_most_expensive_hours_top3",
            "spot_price_daily": "spot_price_daily",
            "demand_forecast": "demand_forecast",
            "demand_programmed": "demand_programmed",
            "wind_forecast": "wind_forecast",
            "solar_forecast": "solar_forecast",
            "wind_real": "wind_real",
        }
        mapped_field = value_map.get(key)
        if mapped_field is None:
            return None
        return getattr(data, mapped_field)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data
        if self.entity_description.key == "current_price":
            day_prices = data.today_prices if isinstance(data.today_prices, list) else []
            hourly_prices: dict[str, float] = {}
            for hour_index in range(24):
                price_value = 0.0
                if hour_index < len(day_prices):
                    row = day_prices[hour_index]
                    if isinstance(row, dict):
                        try:
                            price_value = round(float(row.get("pcb", 0)), 5)
                        except (TypeError, ValueError):
                            price_value = 0.0
                hourly_prices[f"price_{hour_index:02d}h"] = price_value

            return {
                "id": self.unique_id,
                "integration": constants.DOMAIN,
                "relativePrice": data.current_relative_price,
                "dayPrices": data.today_prices,
                "DayPrices": hourly_prices,
                **hourly_prices,
            }

        if self.entity_description.key == "future_day":
            return {
                "id": self.unique_id,
                "integration": constants.DOMAIN,
                "relativePrice": data.future_relative_price,
                "dayPrices": data.future_prices,
            }

        if self.entity_description.key.startswith("pvpc_"):
            return {
                "id": self.unique_id,
                "integration": constants.DOMAIN,
                "dayPrices": data.today_prices,
            }

        indicator_metadata = data.indicators_metadata.get(self.entity_description.key, {})
        return {
            "id": self.unique_id,
            "integration": constants.DOMAIN,
            **indicator_metadata,
        }
