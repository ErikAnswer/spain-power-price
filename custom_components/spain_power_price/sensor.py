"""Spain Power Price sensors (modern architecture)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import constants
from .coordinator import SpainPowerPriceCoordinator


@dataclass(frozen=True)
class SpainPowerPriceSensorDescription:
    """Spain Power Price sensor description."""

    key: str
    name: str
    icon: str
    device_class: str | None = None
    unit_of_measurement: str | None = None


SENSOR_DESCRIPTIONS = (
    SpainPowerPriceSensorDescription(
        key="current_price",
        name="Spain Power Price - PVPC - Current",
        icon="mdi:currency-eur",
        unit_of_measurement=CURRENCY_EURO,
    ),
    SpainPowerPriceSensorDescription(
        key="future_day",
        name="Spain Power Price - PVPC - Date",
        icon="mdi:calendar",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from a config entry."""
    personal_token = entry.data[constants.CONF_PERSONAL_TOKEN]

    coordinator = SpainPowerPriceCoordinator(hass, personal_token)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [SpainPowerPriceSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    )


class SpainPowerPriceSensor(CoordinatorEntity[SpainPowerPriceCoordinator], SensorEntity):
    """Sensor entity for Spain Power Price data."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: SpainPowerPriceCoordinator,
        description: SpainPowerPriceSensorDescription,
    ) -> None:
        """Initialize sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{constants.DOMAIN}_{description.key}"
        self._attr_icon = description.icon
        self._attr_native_unit_of_measurement = description.unit_of_measurement

    @property
    def native_value(self) -> str | float | None:
        """Return native sensor value."""
        data = self.coordinator.data
        if self.entity_description.key == "current_price":
            return data.current_price
        if self.entity_description.key == "future_day":
            return data.future_day
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data
        if self.entity_description.key == "current_price":
            return {
                "id": self.unique_id,
                "integration": constants.DOMAIN,
                "relativePrice": data.current_relative_price,
                "dayPrices": data.today_prices,
            }

        return {
            "id": self.unique_id,
            "integration": constants.DOMAIN,
            "relativePrice": data.future_relative_price,
            "dayPrices": data.future_prices,
        }
