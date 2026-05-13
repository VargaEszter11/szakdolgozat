import logging
import os

import httpx

logger = logging.getLogger(__name__)

AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


AMADEUS_JSON_HEADERS = {
    "Accept": "application/json",
}


async def get_amadeus_token():
    """Get OAuth2 access token from Amadeus API."""
    url = f"{AMADEUS_BASE_URL}/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, data=data, headers=AMADEUS_JSON_HEADERS)
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]

async def nearest_airport(lat, lng, distance_km=200):
    """Return the nearest European airport to given coordinates using Amadeus API."""
    if not (AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET):
        logger.warning("Amadeus credentials missing; nearest airport lookup skipped")
        return None

    try:
        access_token = await get_amadeus_token()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Amadeus OAuth failed (%s): %s",
            e.response.status_code,
            (e.response.text or "")[:300],
        )
        return None
    except httpx.RequestError as e:
        logger.warning("Amadeus OAuth request failed: %s", e)
        return None

    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/airports"
    # API expects integer km, 0–500 (see Airport Nearest Relevant spec).
    radius_km = max(0, min(500, int(round(float(distance_km)))))
    params = {
        "latitude": lat,
        "longitude": lng,
        "radius": radius_km,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        **AMADEUS_JSON_HEADERS,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        body = (e.response.text or "")[:500]
        logger.warning(
            "Amadeus airport lookup failed (%s): %s",
            e.response.status_code,
            body,
        )
        if e.response.status_code >= 500:
            logger.warning(
                "Amadeus test data only covers airport search in US, ES, UK, DE, and IN; "
                "other regions often return 5xx. Use production API (api.amadeus.com + prod keys) "
                "or start from a city in those countries. See: "
                "https://github.com/amadeus4dev/data-collection#testing-apis-data-collection"
            )
        return None
    except httpx.RequestError as e:
        logger.warning("Amadeus airport lookup request failed: %s", e)
        return None
    except ValueError as e:
        logger.warning("Amadeus airport lookup returned invalid JSON: %s", e)
        return None

    airports = data.get("data", [])
    if not airports:
        return None
    
    # Return the first (nearest) airport
    airport = airports[0]
    return {
        "name": airport.get("name"),
        "iata": airport.get("iataCode"),
        "icao": airport.get("icaoCode"),
        "city": airport.get("address", {}).get("cityName"),
        "country": airport.get("address", {}).get("countryCode"),
        "distance_km": airport.get("distance", {}).get("value") if airport.get("distance") else None
    }

async def get_direct_destinations(origin_airport_code: str):
    """Get direct destinations from an airport using Amadeus Direct Destinations API."""
    if not origin_airport_code or not (AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET):
        return []

    try:
        access_token = await get_amadeus_token()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning("Amadeus OAuth failed for direct destinations: %s", e)
        return []

    url = f"{AMADEUS_BASE_URL}/v1/airport/direct-destinations"
    params = {"departureAirportCode": origin_airport_code}
    headers = {
        "Authorization": f"Bearer {access_token}",
        **AMADEUS_JSON_HEADERS,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Amadeus direct-destinations failed (%s): %s",
            e.response.status_code,
            (e.response.text or "")[:500],
        )
        return []
    except httpx.RequestError as e:
        logger.warning("Amadeus direct-destinations request failed: %s", e)
        return []
    except ValueError as e:
        logger.warning("Amadeus direct-destinations invalid JSON: %s", e)
        return []

    destinations = data.get("data", [])
    # Extract destination airport codes and cities
    destination_list = []
    for dest in destinations:
        destination_list.append({
            "iata": dest.get("iataCode"),
            "city": dest.get("address", {}).get("cityName"),
            "country": dest.get("address", {}).get("countryCode")
        })
    
    return destination_list

