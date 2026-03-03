import math
from typing import Optional, Tuple


# Very small offline mapping of key Indian cities/regions to coordinates.
# Used only to roughly decide which alerts are "near" the user.
CITY_COORDS = {
    "chennai": (13.0827, 80.2707),
    "velachery": (12.9815, 80.2176),
    "adyar": (13.0012, 80.2565),
    "t.nagar": (13.0418, 80.2341),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "kolkata": (22.5726, 88.3639),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "ahmedabad": (23.0225, 72.5714),
    "pune": (18.5204, 73.8567),
    "jaipur": (26.9124, 75.7873),
    "kochi": (9.9312, 76.2673),
    "patna": (25.5941, 85.1376),
    "assam": (26.2006, 92.9376),
    "guwahati": (26.1445, 91.7362),
    "bay of bengal": (15.0, 88.0),
    # extra cities for broader coverage
    "madurai": (9.9252, 78.1198),
    "varanasi": (25.3176, 82.9739),
    "lucknow": (26.8467, 80.9462),
    "kanpur": (26.4499, 80.3319),
    "nagpur": (21.1458, 79.0882),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "coimbatore": (11.0168, 76.9558),
    "vijayawada": (16.5062, 80.6480),
    "visakhapatnam": (17.6868, 83.2185),
    "surat": (21.1702, 72.8311),
    "meerut": (28.9845, 77.7064),
    "raipur": (21.2514, 81.6296),
}


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def approx_coords_from_location(location: str) -> Optional[Tuple[float, float]]:
    """
    Try to infer approximate coordinates from a free-text location string
    using the small CITY_COORDS mapping above.
    """
    if not location:
        return None
    loc_lower = location.lower()
    for name, (lat, lon) in CITY_COORDS.items():
        if name in loc_lower:
            return lat, lon
    return None


def effective_radius_km(disaster_type: str) -> float:
    """
    Radius in km used to decide if a disaster is "near" the user.

    - Most hazards: 30km
    - Cyclone / Earthquake: 200km (wider impact area)
    """
    dt = (disaster_type or "").upper()
    if dt in ("CYCLONE", "EARTHQUAKE"):
        return 200.0
    return 30.0

