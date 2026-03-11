import httpx
import os
from typing import List, Dict, Any
from utils.nearest_airport import get_amadeus_token
from utils.coordinates import geocode_place

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


async def search_activities_by_location(lat: float, lon: float, radius: int = 1) -> List[Dict[str, Any]]:
    """Search for activities near a location using Amadeus Activities API."""
    try:
        access_token = await get_amadeus_token()

        url = f"{AMADEUS_BASE_URL}/v1/shopping/activities"
        params = {
            "latitude": lat,
            "longitude": lon,
            "radius": radius
        }
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        return data.get("data", [])
    except Exception as e:
        print(f"Error searching activities: {e}")
        return []


async def get_activity_price(city_name: str, country_code: str, days: int) -> Dict[str, Any]:
    """Get activity costs for a city using Amadeus Activities API."""
    estimated_price_per_day = 40
    try:
        lat, lon = await geocode_place(f"{city_name}, {country_code}")
        activities = await search_activities_by_location(lat, lon)

        if activities:
            prices = []
            for activity in activities:
                amount = activity.get("price", {}).get("amount")
                if amount:
                    try:
                        prices.append(float(amount))
                    except (ValueError, TypeError):
                        pass

            if prices:
                avg_price = sum(prices) / len(prices)
                daily_cost = round(avg_price * 2, 2)
                return {
                    "valid": True,
                    "price": round(daily_cost * days, 2),
                    "price_per_day": daily_cost,
                    "currency": "EUR",
                    "source": "amadeus",
                    "activities_count": len(prices),
                }

        return {
            "valid": True,
            "price": estimated_price_per_day * days,
            "price_per_day": estimated_price_per_day,
            "currency": "EUR",
            "source": "estimated",
            "activities_count": days * 2,
        }
    except Exception as e:
        return {
            "valid": True,
            "price": estimated_price_per_day * days,
            "price_per_day": estimated_price_per_day,
            "currency": "EUR",
            "source": "estimated",
            "error": str(e),
        }
