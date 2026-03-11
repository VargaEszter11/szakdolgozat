import math
from utils.coordinates import geocode_place


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


async def estimate_ground_transport_cost(
    origin_city: str, dest_city: str, transport_type: str
) -> float:
    """Estimate train/bus/ferry cost based on haversine distance between cities."""
    rates = {"train": 0.15, "bus": 0.10, "ferry": 0.12}
    rate = rates.get(transport_type, 0.12)
    try:
        lat1, lon1 = await geocode_place(origin_city)
        lat2, lon2 = await geocode_place(dest_city)
        distance = _haversine_km(lat1, lon1, lat2, lon2)
        return max(10.0, round(distance * rate, 2))
    except Exception:
        return 50.0
