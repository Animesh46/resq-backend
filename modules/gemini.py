"""
Offline NLP helpers and rule-based logic.

This module originally used the Gemini API via `google.genai`. To make the
project work without any external LLM or API calls, all functions below are
implemented with simple, deterministic logic based on keywords.

Public APIs (function signatures and return types) are preserved so the rest
of the codebase does not need to change.
"""

import logging
from datetime import datetime
from typing import List

from config import DISASTER_KEYWORDS
from models import GeminiClassification, DisasterType

logger = logging.getLogger(__name__)


def _detect_disaster_type(text: str) -> DisasterType:
    """Simple keyword-based disaster type detection."""
    lowered = text.lower()
    for dtype, keywords in DISASTER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lowered:
                try:
                    return DisasterType[dtype]
                except KeyError:
                    # If config has a key that does not exist in enum, skip it
                    continue
    return DisasterType.UNKNOWN


def _estimate_severity(text: str) -> int:
    """Rough 1–10 severity score based on strong words."""
    text = text.lower()
    score = 3
    for kw in ["red alert", "severe", "massive", "evacuate", "evacuation", "landfall"]:
        if kw in text:
            score += 2
    for kw in ["orange alert", "heavy rain", "flood", "cyclone", "earthquake"]:
        if kw in text:
            score += 1
    return max(1, min(10, score))


def _estimate_escalation(texts: List[str]) -> float:
    """Return 0–10 escalation score from a list of texts."""
    joined = " ".join(texts).lower()
    score = 4.0
    if any(w in joined for w in ["evacuate", "evacuation", "life threatening", "life-threatening"]):
        score += 3.0
    if any(w in joined for w in ["red alert", "very severe", "severe cyclonic storm"]):
        score += 2.0
    if any(w in joined for w in ["monitoring", "yellow alert", "orange alert"]):
        score += 1.0
    return max(0.0, min(10.0, score))


def _estimate_credibility(text: str) -> float:
    """Heuristic credibility 0–1."""
    lowered = text.lower()
    score = 0.7
    for kw in ["official", "imd", "ndma", "ndrf", "government", "ministry"]:
        if kw in lowered:
            score += 0.1
    for kw in ["rumour", "rumor", "alleged", "unconfirmed", "whatsapp"]:
        if kw in lowered:
            score -= 0.3
    return max(0.0, min(1.0, score))


async def classify_disaster(title: str, body: str) -> GeminiClassification:
    """
    Lightweight, offline classifier:
    - disaster_type: based on keyword mapping in config.DISASTER_KEYWORDS
    - location: best-effort — we keep it as "Unknown" for now
    - severity / escalation / credibility: simple heuristics
    """
    text = f"{title}\n{body}"
    disaster_type = _detect_disaster_type(text)
    severity = _estimate_severity(text)
    escalation_score = _estimate_escalation([text])
    credibility_score = _estimate_credibility(text)

    return GeminiClassification(
        disaster_type=disaster_type,
        location="Unknown",
        severity=severity,
        escalation_score=escalation_score,
        credibility_score=credibility_score,
        summary_en=body[:300] or title[:300],
    )


async def get_escalation_score(texts: list[str]) -> float:
    """Offline escalation score."""
    return _estimate_escalation(texts or [""])


async def get_rumor_score(title: str, body: str) -> float:
    """Offline credibility / rumor score using simple heuristics."""
    return _estimate_credibility(f"{title}\n{body}")


async def translate_text(text: str, target_lang: str) -> str:
    """
    Attempt to translate the given text into *target_lang* using Gemini if the
    client is available.  If no API key is configured (or the call fails) we
    gracefully fall back to returning the original English text.

    The format of *target_lang* should be a two‑letter ISO code supported by
    Gemini ("hi", "ta", "en", "te", "mr", etc.).
    """
    from routers.chat import get_gemini_client

    client = get_gemini_client()
    if not client or not target_lang or target_lang.lower() == "en":
        return text
    try:
        # Simple prompt instructing Gemini to translate
        prompt = f"Translate the following text into {target_lang}:\n\n{text}"
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
    # fallback
    return text


async def generate_action_steps(
    disaster_type: str,
    risk_level: str,
    location: str,
    language: str = "en"
) -> list[str]:
    """
    Offline survival steps generator.

    We keep this simple and deterministic; messages are short and generic.
    """
    base = [
        "Stay calm and do not panic",
        "Follow instructions from local authorities",
        "Move to a safer, elevated location if needed",
        "Keep important documents and emergency kit ready",
        "Call 112 in case of emergency",
    ]

    # Slightly tweak based on disaster type
    dt = (disaster_type or "").upper()
    if dt == "FLOOD":
        base[2] = "Move to higher ground away from water bodies"
    elif dt == "CYCLONE":
        base[2] = "Stay indoors away from windows and glass"
    elif dt == "HEATWAVE":
        base[2] = "Stay in shade or cool places and avoid going out at peak heat"

    return base


async def search_current_disasters() -> list:
    """
    Previously this asked Gemini for current events.

    In offline mode we simply return an empty list; callers already have
    their own fallbacks (RSS / demo alerts).
    """
    return []