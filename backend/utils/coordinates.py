import os
import httpx
from fastapi import HTTPException
from typing import Tuple

from utils.countries import EUROPE_COUNTRY_CODES

# Nominatim requires a descriptive User-Agent (no generic library defaults). See:
# https://operations.osmfoundation.org/policies/nominatim/
_DEFAULT_UA = "TravelApp/1.0 (university project; configure NOMINATIM_USER_AGENT in .env)"

# Nominatim countrycodes uses lowercase ISO-2; skip XK (not in OSM countrycodes).
_GEOCODE_COUNTRYCODES = ",".join(
    sorted(code.lower() for code in EUROPE_COUNTRY_CODES if code != "XK")
)


async def geocode_place(place_name: str, language: str = "en") -> Tuple[float, float]:
    return await _nominatim_search(
        place_name,
        language=language,
        featuretype=None,
    )


async def geocode_city_center(
    city: str,
    country_label: str = "",
    *,
    language: str = "en",
) -> Tuple[float, float]:
    """Geocode a city label, preferring municipality center over airport POIs."""
    city = (city or "").strip()
    if not city:
        raise ValueError("City name is required")
    query = f"{city}, {country_label}".strip(", ") if (country_label or "").strip() else city
    try:
        return await _nominatim_search(
            query,
            language=language,
            featuretype="city",
        )
    except ValueError:
        return await geocode_place(query, language=language)


async def _nominatim_search(
    query: str,
    *,
    language: str = "en",
    featuretype: str | None = None,
) -> Tuple[float, float]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "accept-language": language,
        "countrycodes": _GEOCODE_COUNTRYCODES,
    }
    if featuretype:
        params["featuretype"] = featuretype
    user_agent = (os.getenv("NOMINATIM_USER_AGENT") or "").strip() or _DEFAULT_UA
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise HTTPException(
                    status_code=503,
                    detail="Geocoding service is rate-limited, please try again shortly.",
                ) from exc
            raise HTTPException(status_code=502, detail="Geocoding service error.") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Could not reach geocoding service.") from exc

        results = resp.json()
        if not results:
            raise ValueError(f"Place '{query}' not found online")
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])

        print(f"Geocoded '{query}' to coordinates: ({lat}, {lon})")

        return lat, lon
