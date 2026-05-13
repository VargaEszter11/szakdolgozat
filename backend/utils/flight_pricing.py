import httpx
import os
from typing import Dict, Any, Optional
from utils.nearest_airport import get_amadeus_token, AMADEUS_JSON_HEADERS

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


def summarize_flight_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Extract human-readable schedule + price from an Amadeus v2 flight-offer object."""
    if not offer:
        return {}
    price = offer.get("price") or {}
    summary: Dict[str, Any] = {
        "offer_id": offer.get("id"),
        "total": price.get("total"),
        "currency": price.get("currency", "EUR"),
        "segments": [],
    }
    for itin in offer.get("itineraries") or []:
        for seg in itin.get("segments") or []:
            dep = seg.get("departure") or {}
            arr = seg.get("arrival") or {}
            summary["segments"].append(
                {
                    "from": dep.get("iataCode"),
                    "to": arr.get("iataCode"),
                    "departs": dep.get("at"),
                    "arrives": arr.get("at"),
                    "carrier": seg.get("carrierCode"),
                    "flight_number": seg.get("number"),
                    "duration": seg.get("duration"),
                }
            )
    segs = summary["segments"]
    if segs:
        summary["first_departure"] = segs[0].get("departs")
        summary["last_arrival"] = segs[-1].get("arrives")
    return summary


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
        "Authorization": f"Bearer {access_token}",
        **AMADEUS_JSON_HEADERS,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data.get("data", [])


async def confirm_flight_offer_price(offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Reprice / confirm a Flight Offers Search result via Flight Offers Price API.

    Amadeus expects the **full, unmodified** offer object inside ``flightOffers``.
    See: https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-price/api-reference
    """
    if not offer:
        return None
    access_token = await get_amadeus_token()
    url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-offers/pricing"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **AMADEUS_JSON_HEADERS,
    }
    payload = {
        "data": {
            "type": "flight-offers-pricing",
            "flightOffers": [offer],
        }
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    block = data.get("data")
    if isinstance(block, list) and block and isinstance(block[0], dict):
        block = block[0]
    if not isinstance(block, dict):
        block = {}
    priced = block.get("flightOffers")
    if isinstance(priced, list) and priced:
        return priced[0]
    return None


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
        priced_offer = await confirm_flight_offer_price(cheapest_offer) or cheapest_offer
        price = float(priced_offer.get("price", {}).get("total", 0))
        flight = summarize_flight_offer(priced_offer)

        return {
            "valid": price <= budget,
            "price": price,
            "currency": priced_offer.get("price", {}).get("currency", "EUR"),
            "offer_id": priced_offer.get("id"),
            "flight": flight,
            "reason": "Within budget" if price <= budget else f"Price {price} exceeds budget {budget}",
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
            "Authorization": f"Bearer {access_token}",
            **AMADEUS_JSON_HEADERS,
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
