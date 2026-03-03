"""
Rumor Verification Engine
4-layer confidence scoring system.
"""

import logging
from typing import List, Dict

import httpx

from models import VerificationStatus
from modules import state
from config import VERIFICATION_THRESHOLDS, NEWSDATA_API_KEY

logger = logging.getLogger(__name__)


def compute_source_agreement(disaster_type: str, location: str) -> float:
    """
    Layer 1: Source Agreement Score (0–100)
    How many independent sources report the same disaster in the same location?
    """
    articles = state.raw_articles
    if not articles:
        return 0.0

    location_lower = location.lower()
    matching = [
        a for a in articles
        if a.get("disaster_type") == disaster_type
        and location_lower in a.get("location", "").lower()
    ]

    national_hit = any(a["source_type"] == "national" for a in matching)
    local_hit = any(a["source_type"] == "local" for a in matching)
    count = len(matching)

    score = 0.0
    score += 40 if national_hit else 0
    score += 40 if local_hit else 0
    score += min(count * 5, 20)  # up to 20 bonus for volume

    return round(min(score, 100), 1)


def compute_official_confirmation(disaster_type: str, location: str) -> float:
    """
    Layer 2: Official Confirmation Score (0–100)
    Did trusted external sources (IMD / NDMA / official news) report this?

    For real-time verification we use NewsData.io if configured, scoped to
    very recent articles and the specific location string.
    """
    # Prefer live NewsData.io verification when API key is available
    cleaned_location = (location or "").strip()
    if NEWSDATA_API_KEY and cleaned_location and cleaned_location.lower() != "unknown":
        try:
            # Map disaster type to simple English keywords
            keywords = {
                "FLOOD": "flood OR flooding OR heavy rain",
                "CYCLONE": "cyclone OR storm OR landfall",
                "EARTHQUAKE": "earthquake OR tremor OR seismic",
                "WILDFIRE": "wildfire OR forest fire",
                "HEATWAVE": "heatwave OR heat wave OR extreme heat",
                "LANDSLIDE": "landslide OR mudslide",
                "COLDWAVE": "cold wave OR coldwave OR severe cold",
            }.get(disaster_type, "disaster OR emergency")

            # Restrict to India and a short timeframe (last 6 hours) for real-time checks
            q = f'{keywords} AND "{cleaned_location}"'
            params = {
                "apikey": NEWSDATA_API_KEY,
                "q": q,
                "country": "in",
                "language": "en",
                "timeframe": "6",  # last 6 hours
            }
            # Use "latest" endpoint for timeframe filtering on most plans
            resp = httpx.get("https://newsdata.io/api/1/latest", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", []) or data.get("articles", []) or []
                hits = len(results)
                if hits == 0:
                    return 0.0
                # Scale: 1 article → 60, 2 → 80, 3+ → 100
                if hits == 1:
                    return 60.0
                if hits == 2:
                    return 80.0
                return 100.0
            else:
                logger.warning(f"NewsData.io verification HTTP {resp.status_code} for {disaster_type}@{location}")
        except Exception as e:
            logger.warning(f"NewsData.io verification failed for {disaster_type}@{location}: {e}")

    # Fallback: use in-memory 'official' sources from ingested articles
    articles = state.raw_articles
    location_lower = (location or "").lower()

    official_matches = [
        a for a in articles
        if a.get("source_type") == "official"
        and a.get("disaster_type") == disaster_type
        and location_lower in a.get("location", "").lower()
    ]

    if not official_matches:
        return 0.0

    # More official sources = higher confidence
    return min(len(official_matches) * 33.3, 100)


def compute_data_consistency(
    disaster_type: str,
    weather_intensity: float,
    river_trend_score: float,
) -> float:
    """
    Layer 4: Environmental Data Consistency (0–100)
    Does environmental sensor data match the disaster claim?
    """
    if disaster_type == "FLOOD":
        # Flood must be backed by high rainfall AND rising river
        return (weather_intensity * 0.5 + river_trend_score * 0.5)
    elif disaster_type == "CYCLONE":
        return weather_intensity  # Wind/rain driven
    elif disaster_type == "HEATWAVE":
        # Mocked — would check temperature API
        return 70.0
    elif disaster_type in ("EARTHQUAKE", "LANDSLIDE"):
        # No real-time seismic API in MVP — conservative score
        return 60.0
    elif disaster_type == "WILDFIRE":
        # High temp + low humidity = consistent with wildfire
        return weather_intensity
    return 50.0  # Unknown — neutral


def compute_confidence_score(
    source_agreement: float,
    official_confirmation: float,
    nlp_credibility: float,  # 0–1 from Gemini
    data_consistency: float,
) -> float:
    """
    Final formula:
    Confidence = 0.35 * SourceAgreement
               + 0.30 * OfficialConfirmation
               + 0.20 * NLPCredibility (scaled to 100)
               + 0.15 * DataConsistency
    """
    score = (
        0.35 * source_agreement
        + 0.30 * official_confirmation
        + 0.20 * (nlp_credibility * 100)
        + 0.15 * data_consistency
    )
    return round(min(score, 100), 1)


def get_verification_status(confidence: float) -> VerificationStatus:
    if confidence >= VERIFICATION_THRESHOLDS["VERIFIED"]:
        return VerificationStatus.VERIFIED
    elif confidence >= VERIFICATION_THRESHOLDS["MONITORING"]:
        return VerificationStatus.MONITORING
    else:
        return VerificationStatus.RUMOR


def verify_disaster(
    disaster_type: str,
    location: str,
    nlp_credibility: float,
    weather_intensity: float,
    river_trend_score: float,
) -> Dict:
    """Full 4-layer verification. Returns confidence score + status."""
    source_agreement = compute_source_agreement(disaster_type, location)
    official_confirmation = compute_official_confirmation(disaster_type, location)
    data_consistency = compute_data_consistency(
        disaster_type, weather_intensity, river_trend_score
    )
    confidence = compute_confidence_score(
        source_agreement, official_confirmation, nlp_credibility, data_consistency
    )
    status = get_verification_status(confidence)

    logger.debug(
        f"Verification [{disaster_type}@{location}]: "
        f"src={source_agreement} off={official_confirmation} "
        f"nlp={nlp_credibility:.2f} env={data_consistency} → {confidence}"
    )

    return {
        "confidence_score": confidence,
        "verification_status": status,
        "layers": {
            "source_agreement": source_agreement,
            "official_confirmation": official_confirmation,
            "nlp_credibility": nlp_credibility,
            "data_consistency": data_consistency,
        },
    }
