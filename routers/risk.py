"""
Risk Router
POST /api/risk/score  → compute UDRI for user location
GET  /api/risk/udri   → get current area-wide UDRI
"""

from fastapi import APIRouter

from models import RiskRequest
from modules.environmental import (
    get_weather,
    get_river_data,
    compute_weather_intensity,
    compute_river_trend_score,
)
from modules.risk_engine import compute_risk_score, get_risk_level, RiskInputs
from modules import state
from modules.geo import approx_coords_from_location, distance_km, effective_radius_km

router = APIRouter()


@router.post("/score")
async def get_risk_score(req: RiskRequest):
    """
    Compute personalised UDRI for user's GPS location.
    Finds highest-risk active alert near user.
    """
    lat, lon = req.location.latitude, req.location.longitude

    # Find most relevant alert for this location
    # In production, use PostGIS / geodesic distance
    alerts = state.active_alerts
    if not alerts:
        from routers.alerts import _demo_alerts
        alerts = _demo_alerts()

    # Prefer alerts geographically close to the user
    nearby: list = []
    for a in alerts:
        coords = approx_coords_from_location(a.get("location") or a.get("region") or "")
        if not coords:
            continue
        alat, alon = coords
        d = distance_km(lat, lon, alat, alon)
        radius = effective_radius_km(a.get("disaster_type", ""))
        if d <= radius:
            nearby.append((d, a))

    nearby.sort(key=lambda x: x[0])
    filtered_alerts = [a for _, a in nearby]

    top_alert = filtered_alerts[0] if filtered_alerts else None
    if not top_alert:
        return {"udri": 0, "risk_level": "LOW", "alerts": []}

    # Get weather for user's precise location
    weather = await get_weather("user_location", lat, lon)
    weather_intensity = compute_weather_intensity(weather) if weather else 50

    river = await get_river_data()
    river_trend = compute_river_trend_score(river)

    # Use actual distance to hazard in risk inputs when available
    distance_to_hazard = nearby[0][0] if nearby else 5.0

    inputs = RiskInputs(
        disaster_type=top_alert["disaster_type"],
        weather_intensity=weather_intensity,
        river_trend_score=river_trend,
        nlp_escalation_score=top_alert.get("escalation_score", 5),
        wind_speed=weather.wind_speed if weather else 15,
        temperature=weather.temperature if weather else 35,
        region_spread=min(top_alert.get("source_count", 1) * 10, 100),
        distance_to_hazard_km=distance_to_hazard,
        humidity=weather.humidity if weather else 70,
    )

    score = compute_risk_score(top_alert["disaster_type"], inputs)
    level = get_risk_level(score)

    return {
        "udri": round(score, 1),
        "risk_level": level,
        "primary_threat": top_alert["disaster_type"],
        "location": f"{lat:.4f}, {lon:.4f}",
        "alerts": [a["id"] for a in filtered_alerts[:3]],
        "weather": weather.model_dump() if weather else None,
        "river": river.model_dump() if river else None,
    }


@router.get("/udri")
async def get_area_udri():
    """Get current UDRI based on latest ingested data (no GPS needed)."""
    alerts = state.active_alerts
    if not alerts:
        from routers.alerts import _demo_alerts
        alerts = _demo_alerts()

    if not alerts:
        return {"udri": 0, "risk_level": "LOW"}

    top = alerts[0]
    return {
        "udri": top["risk_score"],
        "risk_level": top["risk_level"],
        "primary_threat": top["disaster_type"],
        "location": top["location"],
        "active_threats": len(alerts),
    }
