"""
Environmental Data Module
Fetches weather, river levels, wind speed, temperature.
"""

import logging
import httpx
from typing import Optional
from config import OPENWEATHER_API_KEY
from models import WeatherData, RiverData
from modules import state

logger = logging.getLogger(__name__)

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"

# India Flood Forecasting Monitoring Portal (public data)
CWC_RSS = "https://ffs.cwc.gov.in/flood_bulletin.xml"


async def get_weather(city: str, lat: float = None, lon: float = None) -> Optional[WeatherData]:
    """Fetch current weather from OpenWeatherMap."""
    if not OPENWEATHER_API_KEY:
        logger.warning("No OpenWeather key — using mock data")
        return _mock_weather(city)

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            if lat and lon:
                url = f"{OPENWEATHER_BASE}/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
            else:
                url = f"{OPENWEATHER_BASE}/weather?q={city},IN&appid={OPENWEATHER_API_KEY}&units=metric"

            resp = await client.get(url)
            d = resp.json()

            weather = WeatherData(
                location=d.get("name", city),
                temperature=d["main"]["temp"],
                humidity=d["main"]["humidity"],
                wind_speed=d["wind"]["speed"],
                wind_direction=d["wind"].get("deg"),
                rainfall_mm=d.get("rain", {}).get("1h", 0.0),
                pressure=d["main"]["pressure"],
                condition=d["weather"][0]["description"],
            )
            state.weather_cache[city] = weather.model_dump()
            return weather
    except Exception as e:
        logger.error(f"Weather fetch error: {e}")
        return _mock_weather(city)


def _mock_weather(city: str) -> WeatherData:
    """Fallback mock weather — used when API key not configured."""
    return WeatherData(
        location=city,
        temperature=35.0,
        humidity=85,
        wind_speed=25.0,
        rainfall_mm=45.0,
        pressure=1005,
        condition="heavy rain",
    )


async def get_river_data(station: str = "Adyar") -> RiverData:
    """
    Fetch river level data.
    Currently returns realistic mock data (CWC API requires registration).
    Replace with actual CWC/WRIS API calls when credentials available.
    """
    # TODO: Replace with actual CWC API endpoint when registered
    # POST https://cwc.gov.in/api/stations/{station}/levels

    mock_data = {
        "Adyar": RiverData(
            station="Adyar, Chennai",
            current_level=8.2,
            danger_level=10.5,
            warning_level=9.0,
            rise_rate=0.52,  # metres/hour
            trend="RISING",
        ),
        "Cooum": RiverData(
            station="Cooum, Chennai",
            current_level=6.1,
            danger_level=8.0,
            warning_level=7.0,
            rise_rate=0.3,
            trend="RISING",
        ),
    }
    data = mock_data.get(station, mock_data["Adyar"])
    state.river_cache[station] = data.model_dump()
    return data


def compute_weather_intensity(weather: WeatherData) -> float:
    """
    Normalize weather data to 0–100 intensity score.
    Used as input to flood/cyclone risk formulas.
    """
    score = 0.0
    # Rainfall contribution (heavy rain = 50mm+)
    score += min(weather.rainfall_mm / 100.0, 1.0) * 50
    # Wind speed (cyclone threshold = 120 km/h → 33 m/s)
    score += min(weather.wind_speed / 33.0, 1.0) * 30
    # Humidity (high humidity = flood risk)
    score += (weather.humidity / 100.0) * 20
    return round(score, 1)


def compute_river_trend_score(river: RiverData) -> float:
    """
    Return 0–100 river risk score.
    Considers proximity to danger level and rise rate.
    """
    if river.danger_level == 0:
        return 0.0
    level_ratio = river.current_level / river.danger_level
    trend_bonus = 20 if river.trend == "RISING" else 0
    score = min(level_ratio * 80, 80) + trend_bonus
    return round(min(score, 100), 1)
