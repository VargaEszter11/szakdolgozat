import json
import httpx
from typing import Tuple

async def geocode_place(place_name: str) -> Tuple[float, float]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place_name,
        "format": "json",
        "limit": 1,
        "countrycodes": "AT,BE,BG,HR,CY,CZ,DK,EE,FI,FR,DE,GR,HU,IS,IE,IT,LV,LT,LU,MT,NL,NO,PL,PT,RO,SK,SI,ES,SE,CH,GB"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            raise ValueError(f"Place '{place_name}' not found online")
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])

        print(f"Geocoded '{place_name}' to coordinates: ({lat}, {lon})")
        
        return lat, lon
