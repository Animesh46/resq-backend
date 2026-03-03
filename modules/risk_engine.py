"""
Universal Disaster Risk Engine (UDRI)
Modular risk calculation for each disaster type.
Returns 0–100 risk index.
"""

from dataclasses import dataclass
from typing import Optional
from models import RiskLevel
from config import RISK_LEVELS


@dataclass
class RiskInputs:
    disaster_type: str
    weather_intensity: float       # 0–100
    river_trend_score: float       # 0–100
    nlp_escalation_score: float    # 0–10 (will be scaled)
    wind_speed: float              # m/s (for cyclone)
    temperature: float             # celsius (for heatwave)
    region_spread: float           # 0–100 (how many sources mention region)
    distance_to_hazard_km: float   # km (cyclone/wildfire distance)
    humidity: float                # 0–100


def compute_flood_risk(inp: RiskInputs) -> float:
    """
    Flood Risk Score =
      0.35 * WeatherIntensity
    + 0.30 * RiverTrend
    + 0.20 * NLPEscalation (scaled to 100)
    + 0.15 * RegionSpread
    """
    return (
        0.35 * inp.weather_intensity
        + 0.30 * inp.river_trend_score
        + 0.20 * (inp.nlp_escalation_score * 10)  # 0–10 → 0–100
        + 0.15 * inp.region_spread
    )


def compute_cyclone_risk(inp: RiskInputs) -> float:
    """
    Cyclone Risk = wind intensity + distance factor + pressure drop proxy
    """
    wind_score = min(inp.wind_speed / 60.0 * 100, 100)  # 60 m/s = max
    proximity_score = max(0, 100 - (inp.distance_to_hazard_km / 5.0))  # 500km = 0 risk
    nlp_scaled = inp.nlp_escalation_score * 10

    return (
        0.40 * wind_score
        + 0.30 * proximity_score
        + 0.20 * nlp_scaled
        + 0.10 * inp.weather_intensity
    )


def compute_earthquake_risk(inp: RiskInputs) -> float:
    """
    Earthquake risk is driven by NLP reports (no real-time seismic API in MVP).
    """
    nlp_scaled = inp.nlp_escalation_score * 10
    return (
        0.60 * nlp_scaled
        + 0.40 * inp.region_spread
    )


def compute_wildfire_risk(inp: RiskInputs) -> float:
    """
    Wildfire risk: temperature + low humidity + wind + proximity
    """
    heat_score = min(max(inp.temperature - 35, 0) / 15.0 * 100, 100)
    dryness_score = 100 - inp.humidity
    proximity_score = max(0, 100 - (inp.distance_to_hazard_km / 2.0))

    return (
        0.30 * heat_score
        + 0.25 * dryness_score
        + 0.25 * proximity_score
        + 0.20 * (inp.nlp_escalation_score * 10)
    )


def compute_heatwave_risk(inp: RiskInputs) -> float:
    """
    Heatwave: high temp sustained, high humidity = dangerous wet bulb temp
    """
    heat_score = min(max(inp.temperature - 38, 0) / 10.0 * 100, 100)
    humidity_bonus = (inp.humidity / 100.0) * 30

    return (
        0.50 * heat_score
        + 0.30 * humidity_bonus
        + 0.20 * (inp.nlp_escalation_score * 10)
    )


def compute_landslide_risk(inp: RiskInputs) -> float:
    """
    Landslide: heavy rain + region reports
    """
    return (
        0.50 * inp.weather_intensity
        + 0.30 * inp.river_trend_score  # proxy for saturation
        + 0.20 * (inp.nlp_escalation_score * 10)
    )


def compute_coldwave_risk(inp: RiskInputs) -> float:
    """
    Cold wave: extreme low temperature
    """
    cold_score = min(max(10 - inp.temperature, 0) / 20.0 * 100, 100)
    return (
        0.60 * cold_score
        + 0.40 * (inp.nlp_escalation_score * 10)
    )


RISK_CALCULATORS = {
    "FLOOD": compute_flood_risk,
    "CYCLONE": compute_cyclone_risk,
    "EARTHQUAKE": compute_earthquake_risk,
    "WILDFIRE": compute_wildfire_risk,
    "HEATWAVE": compute_heatwave_risk,
    "LANDSLIDE": compute_landslide_risk,
    "COLDWAVE": compute_coldwave_risk,
}


def compute_risk_score(disaster_type: str, inputs: RiskInputs) -> float:
    """Dispatch to correct disaster risk calculator. Returns 0–100."""
    calc = RISK_CALCULATORS.get(disaster_type)
    if not calc:
        return 0.0
    return round(min(max(calc(inputs), 0), 100), 1)


def get_risk_level(score: float) -> RiskLevel:
    for level, (low, high) in RISK_LEVELS.items():
        if low <= score < high:
            return RiskLevel(level)
    return RiskLevel.CRITICAL


# ── Timeline Predictor ────────────────────────────────────────────────────────

def predict_timeline_hours(
    disaster_type: str,
    current_river_level: float = 0,
    danger_level: float = 10,
    rise_rate: float = 0.5,
    distance_to_hazard_km: float = 200,
    hazard_speed_kmh: float = 20,
) -> Optional[float]:
    """
    Predict hours until critical impact.
    Returns None if timeline not determinable.
    """
    if disaster_type == "FLOOD":
        if rise_rate <= 0:
            return None
        gap = danger_level - current_river_level
        if gap <= 0:
            return 0.0  # Already critical
        return round(gap / rise_rate, 1)

    elif disaster_type == "CYCLONE":
        if hazard_speed_kmh <= 0:
            return None
        return round(distance_to_hazard_km / hazard_speed_kmh, 1)

    elif disaster_type == "WILDFIRE":
        if hazard_speed_kmh <= 0:
            return None
        return round(distance_to_hazard_km / hazard_speed_kmh, 1)

    return None  # Earthquakes etc. are not predictable this way
