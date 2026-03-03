"""
Shelter Router
GET /api/shelter/nearest  → returns nearest shelters to GPS coords
"""

import math
from fastapi import APIRouter, Query
from models import ShelterInfo

router = APIRouter()

# In production: stored in PostGIS database, loaded from NDMA shelter registry
SHELTERS_DB = [
    {"name": "Chennai Corporation Shelter 1", "address": "Nehru Indoor Stadium, Chennai", "latitude": 13.0827, "longitude": 80.2707, "capacity": 500, "contact": "044-25384500", "is_open": True},
    {"name": "Velachery Shelter", "address": "Velachery Bus Terminus, Chennai", "latitude": 12.9815, "longitude": 80.2176, "capacity": 300, "contact": "044-22200200", "is_open": True},
    {"name": "Adyar Government School Shelter", "address": "Adyar, Chennai", "latitude": 13.0012, "longitude": 80.2565, "capacity": 200, "contact": "112", "is_open": True},
    {"name": "T.Nagar Community Center", "address": "T. Nagar, Chennai", "latitude": 13.0418, "longitude": 80.2341, "capacity": 400, "contact": "044-24340900", "is_open": True},
    {"name": "Egmore Relief Camp", "address": "Egmore, Chennai", "latitude": 13.0732, "longitude": 80.2609, "capacity": 250, "contact": "044-28193401", "is_open": False},
]


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Returns distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


@router.get("/nearest")
async def get_nearest_shelters(
    lat: float = Query(13.0827),
    lon: float = Query(80.2707),
    limit: int = Query(3),
):
    """Returns nearest open shelters sorted by distance."""
    results = []
    for s in SHELTERS_DB:
        dist = _haversine(lat, lon, s["latitude"], s["longitude"])
        results.append({**s, "distance_km": round(dist, 2)})

    results.sort(key=lambda x: x["distance_km"])
    open_shelters = [s for s in results if s["is_open"]]
    return open_shelters[:limit]
