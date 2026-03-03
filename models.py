"""Shared data models for ResQ backend."""

from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class DisasterType(str, Enum):
    FLOOD = "FLOOD"
    CYCLONE = "CYCLONE"
    EARTHQUAKE = "EARTHQUAKE"
    WILDFIRE = "WILDFIRE"
    HEATWAVE = "HEATWAVE"
    LANDSLIDE = "LANDSLIDE"
    COLDWAVE = "COLDWAVE"
    UNKNOWN = "UNKNOWN"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    MONITORING = "MONITORING"
    RUMOR = "RUMOR"


class NewsItem(BaseModel):
    title: str
    summary: str
    source: str
    url: str
    published: Optional[str] = None
    source_type: str  # "national" | "local" | "official"


class GeminiClassification(BaseModel):
    disaster_type: DisasterType
    location: str
    severity: int  # 1–10
    escalation_score: float  # 0–10
    credibility_score: float  # 0–1
    summary_en: str


class WeatherData(BaseModel):
    location: str
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: Optional[float] = None
    rainfall_mm: float
    pressure: float
    condition: str


class RiverData(BaseModel):
    station: str
    current_level: float  # metres
    danger_level: float
    warning_level: float
    rise_rate: float  # metres/hour
    trend: str  # "RISING" | "FALLING" | "STABLE"


class DisasterAlert(BaseModel):
    id: str
    disaster_type: DisasterType
    location: str
    region: str
    risk_score: float  # 0–100
    risk_level: RiskLevel
    verification_status: VerificationStatus
    confidence_score: float  # 0–100
    escalation_score: float
    timeline_hours: Optional[float] = None
    summary: str
    action_steps: List[str] = []
    source_count: int = 0
    last_updated: str


class LocationPayload(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    timestamp: Optional[str] = None
    gps_on: bool = True


class RiskRequest(BaseModel):
    location: LocationPayload
    language: str = "en"


class DistressPayload(BaseModel):
    latitude: float
    longitude: float
    timestamp: str
    battery_percent: int
    disaster_type: Optional[str] = None
    user_name: str
    emergency_contact_phone: str
    emergency_contact_email: str
    language: str = "en"


class SafetyResponse(BaseModel):
    user_id: str
    alert_id: str
    is_safe: bool
    timestamp: str


class TranslateRequest(BaseModel):
    text: str
    target_language: str  # "hi", "ta", "te", "mr", "en"


class ShelterInfo(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    capacity: int
    distance_km: float
    contact: Optional[str] = None
    is_open: bool = True
