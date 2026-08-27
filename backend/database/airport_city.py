"""Helpers for deriving display city names from cached airport rows.

Airport DB ``city`` fields often name the airport municipality or full
facility name. ``CITY_OVERRIDES_BY_IATA`` maps common European hubs to the
tourist city used in plans and Booking.com search (e.g. KRK → Krakow).
``airport_name_as_city`` strips facility words from names when no override exists.
"""
from __future__ import annotations

import re
from typing import Optional


CITY_OVERRIDES_BY_IATA = {
    # Airport names where the leading words are a person/brand/area instead of the city.
    "BBF": "Benidorm",
    "BCM": "Bacau",
    "BHD": "Belfast",
    "BLQ": "Bologna",
    "BUD": "Budapest",
    "BVA": "Paris",
    "CND": "Constanta",
    "FMM": "Memmingen",
    "FCO": "Rome",
    "FRU": "Bishkek",
    "GDN": "Gdansk",
    "GRX": "Granada",
    "HEM": "Helsinki",
    "HEL": "Helsinki",
    "HKV": "Haskovo",
    "KIV": "Chisinau",
    "KRK": "Krakow",
    "LYS": "Lyon",
    "MHG": "Mannheim",
    "OTP": "Bucharest",
    "PMO": "Palermo",
    "PVK": "Preveza",
    "PRG": "Prague",
    "RMI": "Rimini",
    "TGV": "Targovishte",
    "TRF": "Oslo",
    "TSE": "Astana",
    "TSF": "Venice",
    "TXL": "Berlin",
    "WMI": "Warsaw",
}


_FACILITY_WORDS = (
    "airport",
    "aeroport",
    "aeropuerto",
    "aerodrome",
    "airfield",
    "airstrip",
    "altiport",
    "heliport",
    "hidroport",
    "hydroport",
    "lufthavn",
    "flughafen",
    "flugplatz",
    "air base",
    "air force base",
    "naval air station",
    "army heliport",
)

_TRANSPORT_WORDS = (
    "bus station",
    "central station",
    "hauptbahnhof",
    "railway station",
    "rail station",
    "sncf station",
    "tgv station",
    "station",
)


def _first_place_part(value: str) -> str:
    value = re.split(r"\s*/\s*", value, maxsplit=1)[0]
    value = re.split(r"\s+-\s+", value, maxsplit=1)[0]
    return value.strip(" ,-/")


def airport_name_as_city(name: Optional[str], iata: Optional[str]) -> str:
    """Return a city-like label for an airport/station display name."""
    code = (iata or "").strip().upper()
    if code and code in CITY_OVERRIDES_BY_IATA:
        return CITY_OVERRIDES_BY_IATA[code]

    label = (name or code or "").strip()
    if not label:
        return code
    if code and label.upper() == code:
        return code

    label = re.sub(r"\s*\([^)]*\)", "", label).strip()
    label = re.sub(r'\s+["\'].*?["\']', "", label).strip()

    transport_pattern = "|".join(re.escape(word) for word in _TRANSPORT_WORDS)
    label = re.sub(rf"\b(?:{transport_pattern})\b.*$", "", label, flags=re.I).strip()

    facility_pattern = "|".join(re.escape(word) for word in _FACILITY_WORDS)
    facility_match = re.search(rf"\b(?:{facility_pattern})\b", label, flags=re.I)
    if facility_match:
        before = label[: facility_match.start()].strip(" ,-/")
        after = label[facility_match.end() :].strip(" ,-/")
        label = before or after or label

    label = re.sub(r"\b(international|intl\.?|regional|municipal|civilian|public|national)\b", "", label, flags=re.I)
    label = re.sub(r"\s+", " ", label).strip(" ,-/")
    label = _first_place_part(label)

    return label or code
