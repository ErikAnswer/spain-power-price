"""Utility helpers for the Spain Power Price integration."""

from __future__ import annotations

from typing import Any

from homeassistant.util import dt as dt_util

from . import constants


def get_current_date_string() -> str:
    """Return current local date in YYYY-MM-DD format required by ESIOS."""
    return dt_util.now().strftime("%Y-%m-%d")


def get_current_hour() -> int:
    """Return current local hour (0..23)."""
    return dt_util.now().hour


def get_esios_headers(personal_token: str) -> dict[str, str]:
    """Return HTTP headers required to call ESIOS API."""
    return {
        "accept": constants.HEADER_ACCEPT,
        "content-type": constants.HEADER_CONTENT_TYPE,
        constants.HEADER_API_KEY: personal_token,
    }


def convert_mwh_string_to_eur(value: Any, decimals: int = 5) -> float:
    """Convert ESIOS numeric value to EUR value."""
    if value is None:
        return 0.0

    if isinstance(value, str):
        normalized_value = value.replace(",", ".")
    else:
        normalized_value = str(value)

    try:
        parsed_value = float(normalized_value)
    except (TypeError, ValueError):
        return 0.0

    eur_value = parsed_value / 1_000
    return round(eur_value, decimals)
