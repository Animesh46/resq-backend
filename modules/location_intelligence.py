"""
Location Intelligence Database — Real geographical vulnerability data for cities.
This maps actual place names and landmarks to disaster risks.
"""

# Structure: {city: {disaster_type: [vulnerable_areas]}}

LOCATION_VULNERABILITIES = {
    "chennai": {
        "flood": [
            "Marina Beach and Cooum River area",
            "Besant Nagar and T. Nagar (chronic waterlogging)",
            "Velachery and surrounding low-lying zones",
            "Areas near Buckingham Canal",
            "Adyar and Kotturpuram (riverine areas)",
            "ICF area and railway zones",
            "Porur and Tambaram (prone to rapid runoff)",
        ],
        "cyclone": [
            "Coastal areas: Marina, Mylapore, Thiruvanmiyur",
            "High-rise buildings in Marina, Besant Nagar",
            "Open rooftops and balconies (wind exposure)",
            "Slums in peripheral areas (weak structures)",
            "Areas near harbors and fishing communities",
        ],
        "earthquake": [
            "Older colonial buildings in central Chennai",
            "Unreinforced masonry structures in North Chennai",
            "High-density areas without earthquake codes",
            "Areas near old temples and heritage sites",
        ],
    },
    "mumbai": {
        "flood": [
            "Eastern suburbs: Thane, Mulund (major waterlogging)",
            "Low-lying areas in Andheri, Goregaon, Borivali",
            "Slum colonies in creek areas (Mahim, Bandra)",
            "Areas near railway lines (drainage blocked)",
            "Vasai Road and northern suburbs",
            "Kurla and Vithalwadi (chronic flooding)",
        ],
        "cyclone": [
            "Coastal colonies: Colaba, Fort, Marine Drive",
            "High-rise buildings in SoBo (wind tunnels)",
            "Dharavi and coastal slums (weak structures)",
            "Worli and Bandra seafront",
            "Fishing villages in peripheral areas",
        ],
    },
    "bangalore": {
        "flood": [
            "Varthur and Bellandur lake areas (overflow)",
            "Low-lying zones in Whitefield and Marathahalli",
            "Electronics City suburbs (poor drainage)",
            "Areas near Kapra, Kasavanahalli wetlands",
            "Outer Ring Road low points during heavy rain",
        ],
        "cyclone": [
            "Elevated areas with poor structure anchoring",
            "Areas with tall isolated trees (wind hazard)",
            "Slums around airport and outer zones",
        ],
    },
    "delhi": {
        "flood": [
            "Areas near Yamuna riverbanks (Dwarka, East Delhi)",
            "Low-lying zones in Rohini, Chhatarpur",
            "Slums in riverine areas subject to flash floods",
            "Roads near railway underpasses",
        ],
        "heatwave": [
            "Open areas without vegetation: Mehrauli, Kalkaji",
            "Industrial zones: Okhla, Bawana",
            "Slums with minimal shade structures",
            "East Delhi and peripheral areas (higher temps)",
        ],
    },
    "hyderabad": {
        "flood": [
            "Areas near Mula-Mutha and Indrayani rivers",
            "Low-lying zones in Charminar, Old City",
            "Himayat Nagar and surrounding colonies",
            "Areas near Osman Sagar and Hussain Sagar lakes",
        ],
        "cyclone": [
            "Outlying slum areas with weak construction",
            "High-rise buildings without storm reinforcement",
        ],
    },
    "kolkata": {
        "flood": [
            "East Kolkata wetlands and surrounding areas",
            "Low-lying neighborhoods in Sealdah, Park Circus",
            "Areas near Hooghly River tributaries",
            "Slums in southern and eastern zones",
        ],
        "cyclone": [
            "Coastal areas and river-adjacent slums",
            "Older colonial buildings in CBD",
            "High-density areas with poor storm drains",
        ],
    },
    "pune": {
        "flood": [
            "Areas near Mutha and Mula rivers",
            "Low-lying zones in Hadapsar, Bibwewadi",
            "Dapodi and Mananjpur (historical flood zones)",
            "Areas near old dam structures",
        ],
    },
    "ahmedabad": {
        "flood": [
            "Areas near Sabarmati River and banks",
            "Low-lying zones in East Ahmedabad",
            "Slums in riverine flood plains",
            "Areas near lake overflow zones",
        ],
    },
    "puri": {
        "flood": [
            "Beach Road and Jagannath Temple area",
            "Low-lying coastal zones around Puri town",
            "Areas near Chilika Lake inlet",
            "NH-316 corridor prone to overflow",
        ],
        "cyclone": [
            "Coastal market area and fishing zones",
            "Weakly built shacks near the sea",
        ],
    },
}

# Safe evacuation points by city and disaster type
SAFE_EVACUATION_POINTS = {
    "chennai": {
        "flood": [
            "Anna University higher ground, Guindy",
            "Fort St. George area (elevated)",
            "Theosophical Society grounds, Adyar",
            "Park Sheraton and nearby hotels (elevated)",
            "Government school buildings on higher ground",
        ],
        "cyclone": [
            "Interior apartment buildings (away from coast)",
            "Sturdily-built schools and community centers",
            "Government shelters in T. Nagar, Vepery",
            "Red Cross shelters across the city",
        ],
    },
    "mumbai": {
        "flood": [
            "MTNL building, Fort (elevated)",
            "Hospital buildings with upper floors",
            "School buildings in Dadar, Shivaji Park",
            "Mandir areas on elevated ground",
        ],
        "cyclone": [
            "Interior buildings away from coast",
            "Community centers: Shivaji Park, Worli",
            "Government offices and schools",
        ],
    },    "puri": {
        "flood": [
            "Community cyclone shelters near Jagannath Temple",
            "School buildings on higher ground",
        ],
    },}

from . import geo


def resolve_city_input(city: str) -> str:
    """Try to resolve a free-text location to a canonical city key.

    If the provided value exactly matches a known city, return it.  If a
    known city name appears as a substring, use that.  Otherwise we try to
    infer coordinates using :func:`geo.approx_coords_from_location` and pick
    the nearest city for which we actually have data.  The returned string is
    suitable for indexing the vulnerability dictionary; it may be the original
    text if no match was found.
    """
    if not city:
        return ""
    cl = city.lower().strip()

    # direct key match
    if cl in LOCATION_VULNERABILITIES:
        return cl

    # substring match (e.g. user types "parts of chennai")
    for known in LOCATION_VULNERABILITIES:
        if known in cl:
            return known

    # try to approximate via our small coord map
    coords = geo.approx_coords_from_location(city)
    if coords:
        best = None
        bestdist = float("inf")
        for known, (lat, lon) in geo.CITY_COORDS.items():
            if known not in LOCATION_VULNERABILITIES:
                continue
            d = geo.distance_km(coords[0], coords[1], lat, lon)
            if d < bestdist:
                bestdist = d
                best = known
        if best and bestdist < 150:  # within 150km
            return best

    # give up and return the lowered input; higher layers will treat it as
    # "general" if they want.
    return cl


async def get_vulnerable_areas(city: str, disaster_type: str) -> list[str]:
    """Fetch actual vulnerable locations for a city and disaster."""
    resolved = resolve_city_input(city)
    disaster_lower = disaster_type.lower().strip()

    if resolved in LOCATION_VULNERABILITIES:
        if disaster_lower in LOCATION_VULNERABILITIES[resolved]:
            return LOCATION_VULNERABILITIES[resolved][disaster_lower]

    # Generic fallback that mentions the (possibly unrecognised) city
    city_name = resolved.title() if resolved else "your area"
    return [
        f"Low-lying areas in {city_name} near water sources",
        "Densely populated zones with weak structures",
        "Areas with poor drainage infrastructure",
        "Slums and informal settlements",
    ]


async def get_safe_locations(city: str, disaster_type: str) -> list[str]:
    """Fetch safe evacuation points for a city and disaster."""
    resolved = resolve_city_input(city)
    disaster_lower = disaster_type.lower().strip()

    if resolved in SAFE_EVACUATION_POINTS:
        if disaster_lower in SAFE_EVACUATION_POINTS[resolved]:
            return SAFE_EVACUATION_POINTS[resolved][disaster_lower]

    # Generic fallback mentioning the city name
    city_name = resolved.title() if resolved else "your area"
    return [
        f"Government shelters in {city_name} (contact 112 for nearest)",
        "Schools and community centers (higher ground)",
        "Hotels and apartment buildings (sturdy structures)",
        "Ask locals for known safe zones",
    ]


async def get_specific_advice(city: str, disaster_type: str, concern: str) -> str:
    """Get personalized advice based on actual city geography."""
    resolved = resolve_city_input(city)
    vulnerable = await get_vulnerable_areas(city, disaster_type)
    safe = await get_safe_locations(city, disaster_type)

    city_display = resolved.title() if resolved else city.title()
    advice = f"In {city_display} during {disaster_type.upper()}:\n\n"

    if resolved != city.lower().strip():
        advice = (f"(Note: using data for {city_display} based on your location input.)\n\n" + advice)

    advice += "❌ AVOID these areas:\n"
    for area in vulnerable[:4]:  # Top 4
        advice += f"  • {area}\n"

    advice += f"\n✅ SAFE locations to go:\n"
    for location in safe[:3]:  # Top 3
        advice += f"  • {location}\n"

    return advice
