import json
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Any, Tuple
import os

# Load airport dataset
_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_airports_file = os.path.join(_data_dir, "airports_europe.json")
with open(_airports_file, encoding="utf-8") as f:
    AIRPORTS = json.load(f)

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def nearest_airport(lat: float, lon: float) -> Dict[str, Any]:
    """Return the nearest European airport to given coordinates."""
    best = min(AIRPORTS, key=lambda a: haversine(lat, lon, a["lat"], a["lon"]))
    distance = haversine(lat, lon, best["lat"], best["lon"])
    return {
        "name": best["name"],
        "iata": best["iata"],
        "icao": best["icao"],
        "distance_km": round(distance, 2)
    }
