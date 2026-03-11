import httpx
import os
from typing import List, Dict, Any
from utils.nearest_airport import get_amadeus_token
from utils.coordinates import geocode_place

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


async def search_hotels_by_city(city_name: str, country_code: str, check_in: str, check_out: str) -> List[Dict[str, Any]]:
    """Search for hotels in a city using Amadeus Hotel Search API."""
    try:
        access_token = await get_amadeus_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                lat, lon = await geocode_place(f"{city_name}, {country_code}")
            except Exception:
                return []

            url_geo = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/hotels/by-geocode"
            params_geo = {
                "latitude": lat,
                "longitude": lon,
                "radius": 5,
                "radiusUnit": "KM"
            }

            response = await client.get(url_geo, params=params_geo, headers=headers)
            if response.status_code == 200:
                hotel_data = response.json()
                hotel_ids = [hotel.get("hotelId") for hotel in hotel_data.get("data", [])[:5] if hotel.get("hotelId")]

                if hotel_ids:
                    url_offers = f"{AMADEUS_BASE_URL}/v3/shopping/hotel-offers"
                    params_offers = {
                        "hotelIds": ",".join(hotel_ids),
                        "adults": 1,
                        "checkInDate": check_in,
                        "checkOutDate": check_out
                    }

                    response_offers = await client.get(url_offers, params=params_offers, headers=headers)
                    if response_offers.status_code == 200:
                        offers_data = response_offers.json()
                        return offers_data.get("data", [])

        return []
    except Exception as e:
        print(f"Error searching hotels for {city_name}: {e}")
        return []


async def get_hotel_price(city_name: str, country_code: str, check_in: str, check_out: str, nights: int) -> Dict[str, Any]:
    """Get hotel price for a city and date range."""
    estimated_price_per_night = 80
    try:
        hotels = await search_hotels_by_city(city_name, country_code, check_in, check_out)

        if not hotels:
            return {
                "valid": True,
                "price": estimated_price_per_night * nights,
                "price_per_night": estimated_price_per_night,
                "currency": "EUR",
                "source": "estimated"
            }

        cheapest_price = None
        for hotel in hotels:
            offers = hotel.get("offers", [])
            for offer in offers:
                price = offer.get("price", {})
                total = float(price.get("total", "999999"))
                if cheapest_price is None or total < cheapest_price:
                    cheapest_price = total

        if cheapest_price:
            return {
                "valid": True,
                "price": cheapest_price * nights,
                "price_per_night": cheapest_price,
                "currency": "EUR",
                "source": "amadeus"
            }

        return {
            "valid": True,
            "price": estimated_price_per_night * nights,
            "price_per_night": estimated_price_per_night,
            "currency": "EUR",
            "source": "estimated"
        }
    except Exception as e:
        return {
            "valid": True,
            "price": estimated_price_per_night * nights,
            "price_per_night": estimated_price_per_night,
            "currency": "EUR",
            "source": "estimated",
            "error": str(e)
        }
