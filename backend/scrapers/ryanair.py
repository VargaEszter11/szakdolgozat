import requests

from scrapers.base import save_routes

RYANAIR_URL = "https://www.ryanair.com/api/views/locate/3/routes"


HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}


def _iata(value):
    if isinstance(value, str):
        return value.strip().upper()
    if isinstance(value, dict):
        return (value.get("iataCode") or value.get("iata") or "").strip().upper()
    return ""


def normalize_ryanair_route(item):
    origin = _iata(item.get("airportFrom"))
    destination = _iata(item.get("airportTo"))
    airline = (item.get("carrierCode") or "FR").strip().upper()

    if not origin or not destination:
        return None

    return {
        "airline_iata": airline,
        "origin_iata": origin,
        "destination_iata": destination,
    }


def get_ryanair_routes():
    response = requests.get(
        RYANAIR_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected Ryanair routes response format")

    routes = []
    for item in data:
        if not isinstance(item, dict):
            continue
        route = normalize_ryanair_route(item)
        if route:
            routes.append(route)

    return routes


def save_ryanair_routes(routes=None, db=None):
    routes = routes if routes is not None else get_ryanair_routes()
    return save_routes(
        routes,
        db=db,
        default_airline_iata="FR",
        airline_names={"FR": "Ryanair"},
    )


if __name__ == "__main__":
    print(save_ryanair_routes())