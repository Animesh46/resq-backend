"""Centralized config for ResQ backend."""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")          # https://gnews.io — free 100/day
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

#
# Messaging integrations intentionally disabled for now.
#

# NewsData.io API key for real-time news verification
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")

INGESTION_INTERVAL = int(os.getenv("INGESTION_INTERVAL_SECONDS", 120))
SAFETY_LOOP_TIMEOUT = int(os.getenv("SAFETY_LOOP_TIMEOUT_MINUTES", 15))

# ── Disaster Classification Keywords (for RSS fallback filter) ────────────────
DISASTER_KEYWORDS = {
    "FLOOD": ["flood", "flooding", "inundation", "overflow", "deluge", "waterlogging", "बाढ़"],
    "CYCLONE": ["cyclone", "hurricane", "typhoon", "storm", "landfall", "चक्रवात"],
    "EARTHQUAKE": ["earthquake", "tremor", "seismic", "quake", "भूकंप"],
    "WILDFIRE": ["wildfire", "forest fire", "bushfire", "जंगल की आग"],
    "HEATWAVE": ["heatwave", "heat wave", "scorching", "extreme heat", "लू"],
    "LANDSLIDE": ["landslide", "mudslide", "landslip", "भूस्खलन"],
    "COLDWAVE": ["cold wave", "coldwave", "severe cold", "frost", "शीत लहर"],
}

# ── Risk Thresholds ───────────────────────────────────────────────────────────
RISK_LEVELS = {
    "LOW": (0, 30),
    "MODERATE": (30, 60),
    "HIGH": (60, 80),
    "CRITICAL": (80, 100),
}

VERIFICATION_THRESHOLDS = {
    "VERIFIED": 80,
    "MONITORING": 50,
}
