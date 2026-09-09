import re

import requests

from scrapers.base import save_routes

# Fallback versions if the site's current API version can't be discovered live.
# Wizz Air bumps this fairly often, so _discover_api_version() is tried first.
WIZZAIR_API_VERSIONS = (
    "29.15.1",
    "29.15.0",
    "29.14.0",
    "28.10.0",
)

WIZZAIR_SITE_URL = "https://wizzair.com/en-gb"
WIZZAIR_VERSION_PATTERN = re.compile(r"be\.wizzair\.com/(\d+\.\d+\.\d+)")


HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

SITE_HEADERS = {
    "Accept": "text/html",
    "User-Agent": "Mozilla/5.0",
}


def _discover_api_version():
    try:
        response = requests.get(WIZZAIR_SITE_URL, headers=SITE_HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return None

    match = WIZZAIR_VERSION_PATTERN.search(response.text)
    return match.group(1) if match else None

def _iata(value):
    if isinstance(value, str):
        return value.strip().upper()
    if isinstance(value, dict):
        return (value.get("iataCode") or value.get("iata") or "").strip().upper()
    return ""

def normalize_wizzair_route(origin, connection):
    destination = _iata(connection.get("iata"))

    if not origin or not destination:
        return None
    return {
        "airline_iata": "W6",
        "origin_iata": origin,
        "destination_iata": destination,
        "effective_from": connection.get("operationStartDate"),
        "effective_to": connection.get("operationEndDate"),
        "is_seasonal": None,
    }

def get_wizzair_routes():
    discovered_version = _discover_api_version()
    versions = (
        (discovered_version,) + WIZZAIR_API_VERSIONS
        if discovered_version
        else WIZZAIR_API_VERSIONS
    )

    response = None
    last_error = None
    for version in versions:
        try:
            response = requests.get(
                f"https://be.wizzair.com/{version}/Api/asset/map",
                headers=HEADERS,
                timeout=30
            )
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            response = None
            last_error = exc

    if response is None:
        raise last_error or RuntimeError("No Wizz Air map API version worked")

    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected Wizz Air map response format")

    routes = []
    real_station_iatas = {
        _iata(city.get("iata"))
        for city in data.get("cities", [])
        if isinstance(city, dict) and not city.get("isFakeStation")
    }

    for city in data.get("cities", []):
        if not isinstance(city, dict) or city.get("isFakeStation"):
            continue

        origin = _iata(city.get("iata"))
        if not origin:
            continue

        for connection in city.get("connections", []):
            if not isinstance(connection, dict) or connection.get("isDirectFlight") is False:
                continue

            destination = _iata(connection.get("iata"))
            if destination not in real_station_iatas:
                continue

            route = normalize_wizzair_route(origin, connection)
            if route:
                routes.append(route)

    return routes

def save_wizzair_routes(routes=None, db=None):
    routes = routes if routes is not None else get_wizzair_routes()
    return save_routes(
        routes,
        db=db,
        default_airline_iata="W6",
        airline_names={"W6": "Wizz Air"},
    )

if __name__ == "__main__":
    print(save_wizzair_routes())
