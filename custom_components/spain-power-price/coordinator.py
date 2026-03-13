"""Data coordinator for Spain Power Price."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import constants, utils

_LOGGER = logging.getLogger(__name__)


@dataclass
class SpainPowerPriceData:
    """Consolidated data for Spain Power Price entities."""

    today_prices: list[dict[str, Any]]
    future_prices: list[dict[str, Any]]
    current_price: float | None
    current_relative_price: int | None
    future_day: str | None
    future_relative_price: int | None


class SpainPowerPriceCoordinator(DataUpdateCoordinator[SpainPowerPriceData]):
    """Coordinator that centralizes ESIOS API calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        personal_token: str,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize coordinator."""
        self._session = async_create_clientsession(hass)
        self._headers = utils.get_esios_headers(personal_token)
        if update_interval is None:
            update_interval = timedelta(minutes=30)

        super().__init__(
            hass,
            _LOGGER,
            name=constants.DOMAIN,
            update_interval=update_interval,
        )

    async def _async_fetch_json(self, endpoint: str) -> dict[str, Any]:
        """Fetch JSON from an ESIOS endpoint."""
        try:
            async with async_timeout.timeout(15):
                async with self._session.get(endpoint, headers=self._headers) as response:
                    if response.status != 200:
                        raise UpdateFailed(
                            f"HTTP {response.status} while querying ESIOS endpoint {endpoint}"
                        )
                    return await response.json()
        except asyncio.TimeoutError as exc:
            raise UpdateFailed("Timeout while querying ESIOS API") from exc

    def _process_pvpc(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize ESIOS payload and compute relative price buckets."""
        items: list[dict[str, Any]] = []

        min_pcb_value: float | None = None
        max_pcb_value: float | None = None
        min_cym_value: float | None = None
        max_cym_value: float | None = None

        for row in payload.get("PVPC", []):
            pcb_price = utils.convert_mwh_string_to_eur(row.get(constants.FIELD_PCB, "0"))
            cym_price = utils.convert_mwh_string_to_eur(row.get(constants.FIELD_CYM, "0"))

            min_pcb_value = pcb_price if min_pcb_value is None else min(min_pcb_value, pcb_price)
            max_pcb_value = pcb_price if max_pcb_value is None else max(max_pcb_value, pcb_price)
            min_cym_value = cym_price if min_cym_value is None else min(min_cym_value, cym_price)
            max_cym_value = cym_price if max_cym_value is None else max(max_cym_value, cym_price)

            items.append(
                {
                    "id": f"{row.get(constants.FIELD_DAY, 'null')}_{row.get(constants.FIELD_HOUR, 'null')}",
                    "day": row.get(constants.FIELD_DAY, "null"),
                    "hour": row.get(constants.FIELD_HOUR, "null"),
                    "pcb": pcb_price,
                    "pcbRelative": 0,
                    "cym": cym_price,
                    "cymRelative": 0,
                }
            )

        if (
            not items
            or min_pcb_value is None
            or max_pcb_value is None
            or min_cym_value is None
            or max_cym_value is None
        ):
            return items

        pcb_mid_mark = min_pcb_value + ((max_pcb_value - min_pcb_value) / 3)
        pcb_high_mark = pcb_mid_mark + ((max_pcb_value - min_pcb_value) / 3)
        cym_mid_mark = min_cym_value + ((max_cym_value - min_cym_value) / 3)
        cym_high_mark = cym_mid_mark + ((max_cym_value - min_cym_value) / 3)

        for item in items:
            item["pcbRelative"] = (
                0
                if item["pcb"] < pcb_mid_mark
                else (1 if item["pcb"] < pcb_high_mark else 2)
            )
            item["cymRelative"] = (
                0
                if item["cym"] < cym_mid_mark
                else (1 if item["cym"] < cym_high_mark else 2)
            )

        items.sort(key=lambda pvpc: (pvpc["day"], pvpc["hour"]))
        return items

    async def _async_update_data(self) -> SpainPowerPriceData:
        """Fetch and return consolidated entity data."""
        today_endpoint = constants.ENDPOINT_TODAY_PRICE.format(utils.get_current_date_string())
        future_endpoint = constants.ENDPOINT_FUTURE_PRICE

        today_payload, future_payload = await asyncio.gather(
            self._async_fetch_json(today_endpoint),
            self._async_fetch_json(future_endpoint),
        )

        today_prices = self._process_pvpc(today_payload)
        future_prices = self._process_pvpc(future_payload)

        current_index = (
            min(utils.get_current_hour(), len(today_prices) - 1) if today_prices else None
        )
        future_index = (
            min(utils.get_current_hour(), len(future_prices) - 1) if future_prices else None
        )

        return SpainPowerPriceData(
            today_prices=today_prices,
            future_prices=future_prices,
            current_price=(today_prices[current_index]["pcb"] if current_index is not None else None),
            current_relative_price=(
                today_prices[current_index]["pcbRelative"]
                if current_index is not None
                else None
            ),
            future_day=(future_prices[0]["day"] if future_prices else None),
            future_relative_price=(
                future_prices[future_index]["pcbRelative"] if future_index is not None else None
            ),
        )
