import csv
import requests
from io import StringIO

LUFTHANSA_URL = "https://www.lufthansa.com/us/en/localroute"
OPENFLIGHTS_ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"

from scrapers.base import save_routes


HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0",
}


def _route(origin, destination):
    origin = (origin or "").strip().upper()
    destination = (destination or "").strip().upper()
    if len(origin) != 3 or len(destination) != 3 or origin == destination:
        return None
    return {
        "airline_iata": "LH",
        "origin_iata": origin,
        "destination_iata": destination,
        "is_seasonal": None,
    }


def _get_lufthansa_routes_from_site():
    response = requests.get(
        LUFTHANSA_URL,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    html = response.text
    import re

    pattern = re.findall(
        r'"origin":"([A-Z]{3})","destination":"([A-Z]{3})"',
        html,
    )
    routes = []
    seen = set()
    for origin, destination in pattern:
        key = (origin, destination)
        if key in seen:
            continue
        seen.add(key)
        route = _route(origin, destination)
        if route:
            routes.append(route)

    if not routes:
        raise RuntimeError("No Lufthansa routes found in Lufthansa page response")

    return routes


def _get_lufthansa_routes_from_openflights():
    response = requests.get(
        OPENFLIGHTS_ROUTES_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()

    routes = []
    seen = set()
    for row in csv.reader(StringIO(response.text)):
        if len(row) < 8:
            continue
        airline, origin, destination, stops = row[0], row[2], row[4], row[7]
        if airline != "LH" or stops != "0":
            continue
        key = (origin, destination)
        if key in seen:
            continue
        seen.add(key)
        route = _route(origin, destination)
        if route:
            routes.append(route)

    if not routes:
        raise RuntimeError("No Lufthansa routes found in OpenFlights fallback")
    return routes


def get_lufthansa_routes():
    try:
        return _get_lufthansa_routes_from_site()
    except requests.RequestException:
        return _get_lufthansa_routes_from_openflights()
    except RuntimeError:
        return _get_lufthansa_routes_from_openflights()


def save_lufthansa_routes(routes=None, db=None):
    routes = routes if routes is not None else get_lufthansa_routes()
    return save_routes(
        routes,
        db=db,
        default_airline_iata="LH",
        airline_names={"LH": "Lufthansa"},
    )


if __name__ == "__main__":
    print(save_lufthansa_routes())