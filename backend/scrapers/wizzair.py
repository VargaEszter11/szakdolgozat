import requests

from scrapers.base import save_routes

WIZZAIR_URL = "https://be.wizzair.com/28.9.0/Api/asset/map"


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

def normalize_wizzair_route(origin, connection):
    destination = _iata(connection.get("iata"))

    if not origin or not destination:
        return None
    return {
        "airline_iata": "W6",
        "origin_iata": origin,
        "destination_iata": destination
    }

def get_wizzair_routes():
    response = requests.get(
        WIZZAIR_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

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
