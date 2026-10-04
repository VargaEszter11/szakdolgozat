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
    "AHO": "Alghero",
    "ALC": "Alicante",
    "AOI": "Ancona",
    "ATH": "Athens",
    "BBF": "Benidorm",
    "BBU": "Bucharest",
    "BCM": "Bacau",
    "BEG": "Belgrade",
    "BGY": "Milan",
    "BHD": "Belfast",
    "BLQ": "Bologna",
    "BRI": "Bari",
    "BRQ": "Brno",
    "BUD": "Budapest",
    "BVA": "Paris",
    "BZG": "Bydgoszcz",
    "BZY": "Balti",
    "CAG": "Cagliari",
    "CDT": "Castellon",
    "CGN": "Cologne",
    "CIA": "Rome",
    "CND": "Constanta",
    "CTA": "Catania",
    "FCO": "Rome",
    "FLR": "Florence",
    "FMM": "Memmingen",
    "FMO": "Munster",
    "FRU": "Bishkek",
    "GDN": "Gdansk",
    "GHV": "Brasov",
    "GOA": "Genoa",
    "GOT": "Gothenburg",
    "GRO": "Girona",
    "GRX": "Granada",
    "GVA": "Geneva",
    "HAJ": "Hannover",
    "HEL": "Helsinki",
    "HEM": "Helsinki",
    "HHN": "Frankfurt",
    "HKV": "Haskovo",
    "INI": "Nis",
    "JMK": "Mykonos",
    "KEF": "Reykjavik",
    "KIV": "Chisinau",
    "KRK": "Krakow",
    "LBA": "Leeds",
    "LCJ": "Lodz",
    "LDY": "Derry",
    "LEJ": "Leipzig",
    "LIS": "Lisbon",
    "LJU": "Ljubljana",
    "LMP": "Lampedusa",
    "LPI": "Linkoping",
    "LTN": "London",
    "LUX": "Luxembourg",
    "LYS": "Lyon",
    "MHG": "Mannheim",
    "MME": "Durham",
    "MST": "Maastricht",
    "NOC": "Knock",
    "NQY": "Newquay",
    "NRN": "Weeze",
    "NYO": "Stockholm",
    "OPO": "Porto",
    "OSR": "Ostrava",
    "OTP": "Bucharest",
    "PAD": "Paderborn",
    "PEG": "Perugia",
    "PMO": "Palermo",
    "POZ": "Poznan",
    "PRG": "Prague",
    "PVK": "Preveza",
    "QSR": "Salerno",
    "RDO": "Radom",
    "RLG": "Rostock",
    "RMI": "Rimini",
    "RMU": "Murcia",
    "RTM": "Rotterdam",
    "RZE": "Rzeszow",
    "SVQ": "Seville",
    "SZY": "Olsztyn",
    "SZZ": "Szczecin",
    "TAT": "Poprad",
    "TFN": "Tenerife",
    "TFS": "Tenerife",
    "TGM": "Targu Mures",
    "TGV": "Targovishte",
    "TPS": "Trapani",
    "TRF": "Oslo",
    "TRN": "Turin",
    "TSE": "Astana",
    "TSF": "Venice",
    "TSR": "Timisoara",
    "TXL": "Berlin",
    "VCE": "Venice",
    "VOL": "Volos",
    "VRN": "Verona",
    "VST": "Stockholm",
    "VXO": "Vaxjo",
    "WAW": "Warsaw",
    "WMI": "Warsaw",
    "WRO": "Wroclaw",
    "ZAG": "Zagreb",
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


def resolve_display_city(
    name: Optional[str], iata: Optional[str], db_city: Optional[str] = None
) -> str:
    """City label for display, with the code-level override always winning.

    Precedence: ``CITY_OVERRIDES_BY_IATA`` first (so corrections live only in
    code, never need a DB write), then the cached ``db_city`` value, then a
    best-effort label derived from the airport's facility ``name``.
    """
    code = (iata or "").strip().upper()
    if code and code in CITY_OVERRIDES_BY_IATA:
        return CITY_OVERRIDES_BY_IATA[code]
    db_city = (db_city or "").strip()
    if db_city:
        return db_city
    return airport_name_as_city(name, iata)
