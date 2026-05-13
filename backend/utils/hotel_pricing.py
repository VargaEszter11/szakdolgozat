import httpx
import os
from typing import List, Dict, Any
from utils.nearest_airport import get_amadeus_token, AMADEUS_JSON_HEADERS
from utils.coordinates import geocode_place

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


async def search_hotels_by_city(city_name: str, country_code: str, check_in: str, check_out: str) -> List[Dict[str, Any]]:
    """Search for hotels in a city using Amadeus Hotel Search API."""
    try:
        access_token = await get_amadeus_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            **AMADEUS_JSON_HEADERS,
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
    """Get hotel price for a city and date range (Amadeus stay total when available)."""
    estimated_price_per_night = 80
    try:
        hotels = await search_hotels_by_city(city_name, country_code, check_in, check_out)

        if not hotels:
            return {
                "valid": True,
                "price": estimated_price_per_night * nights,
                "price_per_night": estimated_price_per_night,
                "currency": "EUR",
                "source": "estimated",
                "hotel_summary": {
                    "hotel_name": None,
                    "check_in": check_in,
                    "check_out": check_out,
                    "nights": nights,
                    "stay_total": round(estimated_price_per_night * nights, 2),
                    "currency": "EUR",
                    "note": "No Amadeus hotel offers; heuristic estimate.",
                },
            }

        best = None
        for hotel in hotels:
            hblock = hotel.get("hotel") or {}
            hname = hblock.get("name") or hotel.get("name")
            for offer in hotel.get("offers", []) or []:
                price = offer.get("price", {})
                try:
                    stay_total = float(price.get("total", "999999"))
                except (TypeError, ValueError):
                    continue
                if best is None or stay_total < best["stay_total"]:
                    room = (offer.get("room") or {}).get("typeEstimated", {}) or {}
                    best = {
                        "stay_total": stay_total,
                        "currency": price.get("currency") or "EUR",
                        "hotel_name": hname,
                        "room_category": room.get("category"),
                        "check_in": check_in,
                        "check_out": check_out,
                    }

        if best:
            stay = round(best["stay_total"], 2)
            return {
                "valid": True,
                "price": stay,
                "price_per_night": round(stay / max(nights, 1), 2),
                "currency": best["currency"],
                "source": "amadeus",
                "hotel_summary": {
                    "hotel_name": best["hotel_name"],
                    "check_in": best["check_in"],
                    "check_out": best["check_out"],
                    "nights": nights,
                    "stay_total": stay,
                    "currency": best["currency"],
                    "room_category": best["room_category"],
                },
            }

        return {
            "valid": True,
            "price": estimated_price_per_night * nights,
            "price_per_night": estimated_price_per_night,
            "currency": "EUR",
            "source": "estimated",
            "hotel_summary": {
                "hotel_name": None,
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "stay_total": round(estimated_price_per_night * nights, 2),
                "currency": "EUR",
                "note": "Amadeus returned no priced offers; heuristic estimate.",
            },
        }
    except Exception as e:
        return {
            "valid": True,
            "price": estimated_price_per_night * nights,
            "price_per_night": estimated_price_per_night,
            "currency": "EUR",
            "source": "estimated",
            "error": str(e),
            "hotel_summary": {
                "hotel_name": None,
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "stay_total": round(estimated_price_per_night * nights, 2),
                "currency": "EUR",
                "note": "Error while contacting Amadeus; heuristic estimate.",
            },
        }
