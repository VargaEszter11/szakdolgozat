"""Region helpers for cached airports."""

from __future__ import annotations

from typing import Optional


EUROPE_COUNTRY_CODES = {
    "AL", "AD", "AT", "BE", "BA", "BG", "HR", "CY", "CZ", "DK",
    "EE", "FI", "FR", "DE", "GR", "HU", "IS", "IE", "IT", "XK",
    "LV", "LI", "LT", "LU", "MT", "MD", "MC", "ME", "NL", "MK",
    "NO", "PL", "PT", "RO", "RU", "SM", "RS", "SK", "SI", "ES",
    "SE", "CH", "GB", "TR", "UA", "BY", "VA",
}


def is_europe_country(country_code: Optional[str]) -> bool:
    return (country_code or "").strip().upper() in EUROPE_COUNTRY_CODES
