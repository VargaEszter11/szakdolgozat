"""ISO-2 country codes — keep in sync with frontend/scripts/utils/countries.js ROWS."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# Aliases kept for parity with the frontend autocomplete search index.
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
    ("KZ", "Kazakhstan", ("kazahsztan", "kazahstan", "kazahsztán",)),
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

COUNTRY_CODE_TO_NAME: Dict[str, str] = {
    code: name for code, name, _aliases in _COUNTRY_ROWS
}

# Derived from ROWS — same set used by airport region filters and Europe chart.
EUROPE_COUNTRY_CODES = set(COUNTRY_CODE_TO_NAME.keys())


def normalize_country_code(value: Optional[str]) -> Optional[str]:
    """Return ISO-2 code if value is already a known code; no name matching."""
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
    return None


def country_display_name(value: Optional[str]) -> str:
    """Human-readable English name for an ISO-2 country code."""
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
