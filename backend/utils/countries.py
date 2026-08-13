"""ISO-2 country codes — keep in sync with frontend/scripts/utils/countries.js ROWS."""

from __future__ import annotations

import unicodedata
from typing import Dict, List, Optional, Tuple


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", (value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.replace("-", " ").replace("_", " ").split())

_COUNTRY_ROWS: List[Tuple[str, str, Tuple[str, ...]]] = [
    ("AL", "Albania", ("albania", "albánia", "albanien",)),
    ("AD", "Andorra", ()),
    ("AM", "Armenia", ("armenia", "örményország", "ormenyorszag")),
    ("AT", "Austria", ("osterreich", "österreich", "ausztria",)),
    ("AZ", "Azerbaijan", ("azerbaijan",)),
    ("BY", "Belarus", ("weissrussland", "weißrussland", "belarus", "feherorosz", "fehérorosz",)),
    ("BE", "Belgium", ("belgien", "belgium", "belgique", "belgie",)),
    ("BA", "Bosnia and Herzegovina", ("bosnia", "bosnien", "bosznia", "bosznia-hercegovina",)),
    ("BG", "Bulgaria", ("bulgarien", "bulgaria", "bulgária",)),
    ("HR", "Croatia", ("kroatien", "horvatorszag", "horvátország", "croatia",)),
    ("CY", "Cyprus", ("zypern", "ciprus",)),
    ("CZ", "Czechia", ("czech republic", "tschechien", "cseh", "csehorszag", "csehország",)),
    ("DK", "Denmark", ("danemark", "dänemark", "dania", "dánia",)),
    ("EE", "Estonia", ("estland", "esztorszag", "észtország",)),
    ("FI", "Finland", ("finnland", "finnorszag", "finnország",)),
    ("FR", "France", ("frankreich", "francia", "franciaorszag", "franciaország",)),
    ("GE", "Georgia", ("georgia", "grúzia", "gruzie", "gruzia")),
    ("DE", "Germany", ("deutschland", "nemetorszag", "németország",)),
    ("GR", "Greece", ("griechenland", "gorogorszag", "görögország",)),
    ("HU", "Hungary", ("magyarorszag", "magyarország", "ungarn",)),
    ("IS", "Iceland", ("island", "izland", "ízland")),
    ("IE", "Ireland", ("irland", "irorszag", "írország",)),
    ("IT", "Italy", ("italien", "italia", "olaszorszag", "olaszország",)),
    ("KA", "Kazakhstan", ("kazahsztan", "kazahstan", "kazahsztán",)),
    ("XK", "Kosovo", ("koszovo", "koszovó", )),
    ("LV", "Latvia", ("lettland", "lettorszag", "lettország",)),
    ("LI", "Liechtenstein", ()),
    ("LT", "Lithuania", ("litauen", "litvania", "litvánia",)),
    ("LU", "Luxembourg", ("luxemburg",)),
    ("MT", "Malta", ("málta",)),
    ("MD", "Moldova", ("moldawien", "moldova",)),
    ("MC", "Monaco", ()),
    ("ME", "Montenegro", ("crna gora", "montenegró")),
    ("NL", "Netherlands", ("holland", "hollandia", "niederlande", "the netherlands",)),
    ("MK", "North Macedonia", ("macedonia", "mazedonien", "eszak-macedonia", "észak-macedónia", "macedónia")),
    ("NO", "Norway", ("norwegen", "norvegia", "norvégia",)),
    ("PL", "Poland", ("polen", "lengyelorszag", "lengyelország",)),
    ("PT", "Portugal", ("portugalia", "portugália",)),
    ("RO", "Romania", ("rumänien", "rumanien", "romania", "románia")),
    ("RU", "Russia", ("russia", "oroszország", "oroszorszag",)),
    ("SM", "San Marino", ()),
    ("RS", "Serbia", ("serbien", "szerbia",)),
    ("SK", "Slovakia", ("slowakei", "szlovakia", "szlovákia",)),
    ("SI", "Slovenia", ("slowenien", "szlovenia", "szlovénia",)),
    ("ES", "Spain", ("spanien", "espana", "españa", "spanyolorszag", "spanyolország",)),
    ("SE", "Sweden", ("schweden", "svedorszag", "svédország",)),
    ("CH", "Switzerland", ("schweiz", "suisse", "svizzera", "svajc", "svájc")),
    ("TR", "Turkey", ("türkei", "turkey", "törökország", "torokorszag")),
    ("UA", "Ukraine", ("ukraine", "ukrajna",)),
    ("GB", "United Kingdom", ("uk", "great britain", "england", "scotland", "wales", "grossbritannien", "nagy-britannia", "egyesult kiralysag", "egyesült királyság", "anglia")),
    ("VA", "Vatican City", ("vatican", "holy see", "vatikan", "vatikanvaros", "vatikánváros",)),
]

COUNTRY_CODE_TO_NAME: Dict[str, str] = {}
COUNTRY_NAME_TO_CODE: Dict[str, str] = {}

for _code, _name, _aliases in _COUNTRY_ROWS:
    COUNTRY_CODE_TO_NAME[_code] = _name
    COUNTRY_NAME_TO_CODE[_fold(_name)] = _code
    for _alias in _aliases:
        COUNTRY_NAME_TO_CODE[_fold(_alias)] = _code

# Derived from ROWS — same set used by airport region filters and Europe chart.
EUROPE_COUNTRY_CODES = set(COUNTRY_CODE_TO_NAME.keys())


def normalize_country_code(value: Optional[str]) -> Optional[str]:
    """Return ISO-2 code from the country list, or None."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper == "UK":
        upper = "GB"
    if len(upper) == 2 and upper.isalpha():
        return upper if upper in COUNTRY_CODE_TO_NAME else None
    folded = _fold(raw)
    if folded in COUNTRY_NAME_TO_CODE:
        return COUNTRY_NAME_TO_CODE[folded]
    for name, code in COUNTRY_NAME_TO_CODE.items():
        if len(name) >= 4 and (name in folded or folded in name):
            return code
    return None


def country_display_name(value: Optional[str]) -> str:
    """Human-readable English name for a code or legacy free-text value."""
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    code = normalize_country_code(raw)
    if code and code in COUNTRY_CODE_TO_NAME:
        return COUNTRY_CODE_TO_NAME[code]
    return raw


def geocode_country_label(value: Optional[str]) -> str:
    """Prefer a full country name for geocoding queries."""
    return country_display_name(value) or (str(value).strip() if value else "")
