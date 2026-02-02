import httpx
import os

AMADEUS_CLIENT_ID = "7hA3yhRNp2yxMhuAmqEpUv31NriVXpQ3"
AMADEUS_CLIENT_SECRET = "bD47XfCmmRgnRnIZ"
AMADEUS_BASE_URL = "https://test.api.amadeus.com"

async def get_amadeus_token():
    """Get OAuth2 access token from Amadeus API."""
    url = f"{AMADEUS_BASE_URL}/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]

async def nearest_airport(lat, lng, distance_km=200):
    """Return the nearest European airport to given coordinates using Amadeus API."""
    # Get access token
    access_token = await get_amadeus_token()
    
    # Call Airport Nearest Relevant API
    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/airports"
    params = {
        "latitude": lat,
        "longitude": lng,
        "radius": distance_km
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    
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
    # Get access token
    access_token = await get_amadeus_token()
    
    # Call Direct Destinations API
    url = f"{AMADEUS_BASE_URL}/v1/airport/direct-destinations"
    params = {
        "departureAirportCode": origin_airport_code
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    
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

