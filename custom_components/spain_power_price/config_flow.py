"""Config flow for Spain Power Price."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .constants import (
    CONF_PERSONAL_TOKEN,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ENDPOINT_FUTURE_PRICE,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
)
from .utils import get_esios_headers


async def _async_validate_token(hass, personal_token: str) -> bool:
    """Validate token by calling ESIOS endpoint."""
    session = async_create_clientsession(hass)

    try:
        async with session.get(
            ENDPOINT_FUTURE_PRICE,
            headers=get_esios_headers(personal_token),
            timeout=15,
        ) as response:
            return response.status == 200
    except Exception:
        return False


class SpainPowerPriceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Spain Power Price."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            personal_token = user_input[CONF_PERSONAL_TOKEN].strip()

            if len(personal_token) != 64:
                errors[CONF_PERSONAL_TOKEN] = "invalid_token"
            else:
                try:
                    int(personal_token, 16)
                except ValueError:
                    errors[CONF_PERSONAL_TOKEN] = "invalid_token"
                else:
                    if not await _async_validate_token(self.hass, personal_token):
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(DOMAIN)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title="Spain Power Price",
                            data={CONF_PERSONAL_TOKEN: personal_token},
                        )

        schema = vol.Schema({vol.Required(CONF_PERSONAL_TOKEN): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return options flow for this handler."""
        return SpainPowerPriceOptionsFlow(config_entry)


class SpainPowerPriceOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Spain Power Price."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = int(
            self.config_entry.options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
            )
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    default=current_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_UPDATE_INTERVAL_MINUTES,
                        max=MAX_UPDATE_INTERVAL_MINUTES,
                    ),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
