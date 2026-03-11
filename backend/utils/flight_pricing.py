import httpx
import os
from typing import Dict, Any, Optional
from utils.nearest_airport import get_amadeus_token

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


async def search_flight_offers(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None):
    """Search for flight offers between two airports using Amadeus Flight Offers Search API."""
    access_token = await get_amadeus_token()

    url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": 1,
        "max": 5
    }

    if return_date:
        params["returnDate"] = return_date

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data.get("data", [])


async def get_flight_price(offer_id: str):
    """Get confirmed price for a flight offer using Amadeus Flight Offers Price API."""
    access_token = await get_amadeus_token()

    url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-offers/pricing"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json={"data": {"type": "flight-offer", "id": offer_id}}, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data.get("data", {})


async def validate_plan_segment(origin_airport: str, dest_airport: str, date: str, budget: float) -> Dict[str, Any]:
    """Validate a single flight segment and get pricing information."""
    try:
        offers = await search_flight_offers(origin_airport, dest_airport, date)

        if not offers:
            return {
                "valid": False,
                "reason": "No flights available",
                "price": None
            }

        cheapest_offer = min(offers, key=lambda x: float(x.get("price", {}).get("total", "999999")))
        price = float(cheapest_offer.get("price", {}).get("total", 0))

        return {
            "valid": price <= budget,
            "price": price,
            "currency": cheapest_offer.get("price", {}).get("currency", "EUR"),
            "offer_id": cheapest_offer.get("id"),
            "reason": "Within budget" if price <= budget else f"Price {price} exceeds budget {budget}"
        }
    except Exception as e:
        return {
            "valid": False,
            "reason": f"Error validating flight: {str(e)}",
            "price": None
        }


async def get_city_airport_code(city_name: str, country_code: str = None) -> Optional[str]:
    """Get airport IATA code for a city using Amadeus Airport & City Search API."""
    try:
        access_token = await get_amadeus_token()

        url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations"
        params = {
            "subType": "AIRPORT",
            "keyword": city_name,
            "max": 1
        }

        if country_code:
            params["countryCode"] = country_code

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        airports = data.get("data", [])
        if airports:
            return airports[0].get("iataCode")

        return None
    except Exception as e:
        print(f"Error getting airport code for {city_name}: {e}")
        return None
