import asyncio
import os
import time
import httpx
from fastapi import HTTPException
from typing import Tuple

from utils.countries import EUROPE_COUNTRY_CODES

# Nominatim requires a descriptive User-Agent (no generic library defaults). See:
# https://operations.osmfoundation.org/policies/nominatim/
_DEFAULT_UA = "Planventure/1.0 (university project; configure NOMINATIM_USER_AGENT in .env)"

# Nominatim's usage policy caps requests at 1/second. This gates every call made
# through _nominatim_search (regardless of caller or concurrency) behind a single
# shared minimum-interval lock, process-wide - in-process only, see stress test
# report for the multi-replica caveat.
_NOMINATIM_MIN_INTERVAL_SECONDS = 1.1
_nominatim_rate_lock = asyncio.Lock()
_nominatim_next_allowed_at = 0.0


async def _throttle_nominatim() -> None:
    global _nominatim_next_allowed_at
    async with _nominatim_rate_lock:
        now = time.monotonic()
        if now < _nominatim_next_allowed_at:
            await asyncio.sleep(_nominatim_next_allowed_at - now)
            now = time.monotonic()
        _nominatim_next_allowed_at = now + _NOMINATIM_MIN_INTERVAL_SECONDS

# Nominatim countrycodes uses lowercase ISO-2; skip XK (not in OSM countrycodes).
_GEOCODE_COUNTRYCODES = ",".join(
    sorted(code.lower() for code in EUROPE_COUNTRY_CODES if code != "XK")
)


async def geocode_place(place_name: str, language: str = "en") -> Tuple[float, float]:
    lat, lon, _country = await _nominatim_search(
        place_name,
        language=language,
        featuretype=None,
        addressdetails=False,
    )
    return lat, lon


async def geocode_place_with_country(
    place_name: str, language: str = "en"
) -> Tuple[float, float, str]:
    """Like geocode_place, but also returns an ISO-2 country code when Nominatim provides one."""
    return await _nominatim_search(
        place_name,
        language=language,
        featuretype=None,
        addressdetails=True,
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
        lat, lon, _country = await _nominatim_search(
            query,
            language=language,
            featuretype="city",
            addressdetails=False,
        )
        return lat, lon
    except ValueError:
        return await geocode_place(query, language=language)


async def _nominatim_search(
    query: str,
    *,
    language: str = "en",
    featuretype: str | None = None,
    addressdetails: bool = False,
) -> Tuple[float, float, str]:
    await _throttle_nominatim()
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
    if addressdetails:
        params["addressdetails"] = "1"
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
        hit = results[0]
        lat = float(hit["lat"])
        lon = float(hit["lon"])
        country = ""
        if addressdetails:
            addr = hit.get("address") or {}
            raw = str(addr.get("country_code") or "").strip().upper()
            if raw == "UK":
                raw = "GB"
            country = raw

        print(f"Geocoded '{query}' to coordinates: ({lat}, {lon})")

        return lat, lon, country
