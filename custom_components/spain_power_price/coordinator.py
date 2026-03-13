"""Data coordinator for Spain Power Price."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any

import async_timeout
from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
    pvpc_average_price: float | None
    pvpc_min_price: float | None
    pvpc_max_price: float | None
    pvpc_cheapest_hour: str | None
    pvpc_most_expensive_hour: str | None
    pvpc_cheapest_hours_top3: str | None
    spot_price_daily: float | None
    demand_forecast: float | None
    demand_programmed: float | None
    wind_forecast: float | None
    solar_forecast: float | None
    wind_real: float | None
    indicators_metadata: dict[str, dict[str, Any]]


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
        except ClientError as exc:
            raise UpdateFailed(f"Network error while querying ESIOS API: {exc}") from exc
        except ValueError as exc:
            raise UpdateFailed("Invalid JSON returned by ESIOS API") from exc

    @staticmethod
    def _empty_data() -> SpainPowerPriceData:
        """Return an empty data object for safe startup fallback."""
        return SpainPowerPriceData(
            today_prices=[],
            future_prices=[],
            current_price=None,
            current_relative_price=None,
            future_day=None,
            future_relative_price=None,
            pvpc_average_price=None,
            pvpc_min_price=None,
            pvpc_max_price=None,
            pvpc_cheapest_hour=None,
            pvpc_most_expensive_hour=None,
            pvpc_cheapest_hours_top3=None,
            spot_price_daily=None,
            demand_forecast=None,
            demand_programmed=None,
            wind_forecast=None,
            solar_forecast=None,
            wind_real=None,
            indicators_metadata={},
        )

    @staticmethod
    def _parse_local_datetime(datetime_value: Any) -> datetime | None:
        """Parse datetime string from ESIOS payload and convert to local tz."""
        if not isinstance(datetime_value, str):
            return None

        parsed = dt_util.parse_datetime(datetime_value)
        if parsed is None:
            return None

        local_tz = dt_util.now().tzinfo
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=local_tz)

        return parsed.astimezone(local_tz)

    @staticmethod
    def _preferred_geo_rank(geo_name: str) -> int:
        """Return preference rank for geo names (lower is better)."""
        normalized_geo_name = geo_name.lower()
        if "pení" in normalized_geo_name or "peni" in normalized_geo_name:
            return 0
        if "espa" in normalized_geo_name or "spain" in normalized_geo_name:
            return 1
        return 2

    def _extract_current_indicator_value(
        self, payload: dict[str, Any], indicator_id: int
    ) -> tuple[float | None, dict[str, Any]]:
        """Extract current-hour value from an indicator payload."""
        indicator = payload.get("indicator", {})
        values = indicator.get("values", [])
        if not isinstance(values, list):
            return None, {"indicator_id": indicator_id}

        now = dt_util.now()
        current_hour_values: list[tuple[int, datetime, dict[str, Any]]] = []
        latest_today: tuple[datetime, dict[str, Any]] | None = None

        for item in values:
            if not isinstance(item, dict):
                continue

            local_datetime = self._parse_local_datetime(item.get("datetime"))
            if local_datetime is None:
                continue

            if local_datetime.date() != now.date():
                continue

            if latest_today is None or local_datetime > latest_today[0]:
                latest_today = (local_datetime, item)

            if local_datetime.hour != now.hour:
                continue

            geo_name = str(item.get("geo_name", ""))
            current_hour_values.append(
                (self._preferred_geo_rank(geo_name), local_datetime, item)
            )

        selected_item: dict[str, Any] | None = None
        selected_datetime: datetime | None = None
        if current_hour_values:
            current_hour_values.sort(key=lambda value: (value[0], value[1]))
            _, selected_datetime, selected_item = current_hour_values[0]
        elif latest_today is not None:
            selected_datetime, selected_item = latest_today

        if selected_item is None:
            return None, {"indicator_id": indicator_id}

        raw_value = selected_item.get("value")
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = None

        metadata = {
            "indicator_id": indicator_id,
            "indicator_name": indicator.get("name"),
            "geo_name": selected_item.get("geo_name"),
            "geo_id": selected_item.get("geo_id"),
            "datetime": selected_datetime.isoformat() if selected_datetime else None,
        }
        return value, metadata

    def _compute_pvpc_stats(self, today_prices: list[dict[str, Any]]) -> dict[str, float | str | None]:
        """Compute derived daily PVPC statistics."""
        if not today_prices:
            return {
                "average": None,
                "minimum": None,
                "maximum": None,
                "cheapest_hour": None,
                "most_expensive_hour": None,
                "top3_cheapest_hours": None,
            }

        prices = [item["pcb"] for item in today_prices if isinstance(item.get("pcb"), (int, float))]
        if not prices:
            return {
                "average": None,
                "minimum": None,
                "maximum": None,
                "cheapest_hour": None,
                "most_expensive_hour": None,
                "top3_cheapest_hours": None,
            }

        cheapest = min(today_prices, key=lambda item: item.get("pcb", float("inf")))
        most_expensive = max(today_prices, key=lambda item: item.get("pcb", float("-inf")))
        top3 = sorted(today_prices, key=lambda item: item.get("pcb", float("inf")))[:3]

        return {
            "average": round(sum(prices) / len(prices), 5),
            "minimum": round(min(prices), 5),
            "maximum": round(max(prices), 5),
            "cheapest_hour": str(cheapest.get("hour")),
            "most_expensive_hour": str(most_expensive.get("hour")),
            "top3_cheapest_hours": ", ".join(str(item.get("hour")) for item in top3),
        }

    def _process_pvpc(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize ESIOS payload and compute relative price buckets."""
        items: list[dict[str, Any]] = []
        rows = payload.get("PVPC", [])
        if not isinstance(rows, list):
            return items

        min_pcb_value: float | None = None
        max_pcb_value: float | None = None
        min_cym_value: float | None = None
        max_cym_value: float | None = None

        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                pcb_price = utils.convert_mwh_string_to_eur(row.get(constants.FIELD_PCB, "0"))
                cym_price = utils.convert_mwh_string_to_eur(row.get(constants.FIELD_CYM, "0"))
            except (TypeError, ValueError):
                continue

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

        start_date = dt_util.now().date() - timedelta(days=1)
        end_date = dt_util.now().date() + timedelta(days=1)

        indicator_definitions = {
            "spot_price_daily": constants.INDICATOR_SPOT_PRICE_DAILY,
            "demand_forecast": constants.INDICATOR_DEMAND_FORECAST,
            "demand_programmed": constants.INDICATOR_DEMAND_PROGRAMMED,
            "wind_forecast": constants.INDICATOR_WIND_FORECAST,
            "solar_forecast": constants.INDICATOR_SOLAR_FORECAST,
            "wind_real": constants.INDICATOR_WIND_REAL,
        }

        indicator_endpoints = {
            key: constants.ENDPOINT_INDICATOR_RANGE.format(
                indicator_id=indicator_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            for key, indicator_id in indicator_definitions.items()
        }

        fetch_tasks = [
            self._async_fetch_json(today_endpoint),
            self._async_fetch_json(future_endpoint),
        ]
        fetch_tasks.extend(
            self._async_fetch_json(endpoint) for endpoint in indicator_endpoints.values()
        )

        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        today_result = results[0]
        future_result = results[1]
        indicator_results = results[2:]

        today_payload: dict[str, Any] = {}
        future_payload: dict[str, Any] = {}

        if isinstance(today_result, Exception):
            _LOGGER.warning("Could not refresh today PVPC data: %s", today_result)
        else:
            today_payload = today_result

        if isinstance(future_result, Exception):
            _LOGGER.warning("Could not refresh future PVPC data: %s", future_result)
        else:
            future_payload = future_result

        if not today_payload and not future_payload:
            if self.data is not None:
                _LOGGER.warning("Using last known data due to endpoint errors")
                return self.data
            _LOGGER.warning("Using empty data due to initial endpoint errors")
            return self._empty_data()

        today_prices = self._process_pvpc(today_payload)
        future_prices = self._process_pvpc(future_payload)

        current_index = (
            min(utils.get_current_hour(), len(today_prices) - 1) if today_prices else None
        )
        future_index = (
            min(utils.get_current_hour(), len(future_prices) - 1) if future_prices else None
        )

        pvpc_stats = self._compute_pvpc_stats(today_prices)

        indicator_values: dict[str, float | None] = {key: None for key in indicator_definitions}
        indicators_metadata: dict[str, dict[str, Any]] = {}

        for (sensor_key, indicator_id), indicator_result in zip(
            indicator_definitions.items(), indicator_results
        ):
            if isinstance(indicator_result, Exception):
                _LOGGER.warning(
                    "Could not refresh indicator %s (%s): %s",
                    sensor_key,
                    indicator_id,
                    indicator_result,
                )
                indicators_metadata[sensor_key] = {"indicator_id": indicator_id}
                continue

            value, metadata = self._extract_current_indicator_value(indicator_result, indicator_id)
            indicator_values[sensor_key] = value
            indicators_metadata[sensor_key] = metadata

        spot_raw_value = indicator_values["spot_price_daily"]
        spot_eur_value = (
            utils.convert_mwh_string_to_eur(spot_raw_value) if spot_raw_value is not None else None
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
            pvpc_average_price=pvpc_stats["average"],
            pvpc_min_price=pvpc_stats["minimum"],
            pvpc_max_price=pvpc_stats["maximum"],
            pvpc_cheapest_hour=pvpc_stats["cheapest_hour"],
            pvpc_most_expensive_hour=pvpc_stats["most_expensive_hour"],
            pvpc_cheapest_hours_top3=pvpc_stats["top3_cheapest_hours"],
            spot_price_daily=spot_eur_value,
            demand_forecast=indicator_values["demand_forecast"],
            demand_programmed=indicator_values["demand_programmed"],
            wind_forecast=indicator_values["wind_forecast"],
            solar_forecast=indicator_values["solar_forecast"],
            wind_real=indicator_values["wind_real"],
            indicators_metadata=indicators_metadata,
        )
