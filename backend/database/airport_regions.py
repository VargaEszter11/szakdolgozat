"""Region helpers for cached airports."""

from __future__ import annotations

from typing import Optional

from utils.countries import EUROPE_COUNTRY_CODES


def is_europe_country(country_code: Optional[str]) -> bool:
    return (country_code or "").strip().upper() in EUROPE_COUNTRY_CODES
