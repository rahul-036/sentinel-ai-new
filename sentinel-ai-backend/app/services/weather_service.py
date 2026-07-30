"""
WeatherService — live weather data from WeatherAPI.com.

Responsibilities:
  1. Fetch current conditions for a location via the WeatherAPI current.json endpoint.
  2. Evaluate weather risk (Low / Medium / High) from the raw conditions.
  3. Return a fully-populated WeatherAnalysis schema.
  4. On any failure (missing key, network error, bad response) log a warning
     and return mock data so the agent never crashes.

Risk evaluation rules (applied in priority order):
  Condition contains "thunder"          → High   (score 20)
  Condition contains "heavy rain"       → High   (score 30)
  Visibility < 2 km                     → High   (score 30)
  Condition contains "fog" or "mist"    → Medium (score 50)
  Wind speed > 40 km/h                  → Medium (score 55)
  Condition contains "rain" or "drizzle"→ Medium (score 60)
  Everything else (clear, cloudy, etc.) → Low    (score 85)
"""

import httpx
import structlog

from app.core.config import get_settings
from app.schemas.risk import WeatherAnalysis

logger = structlog.get_logger(__name__)

_WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
_TIMEOUT_SECONDS = 8.0


# ---------------------------------------------------------------------------
# Risk evaluation
# ---------------------------------------------------------------------------

def _evaluate_weather_risk(
    condition: str,
    wind_kph: float,
    visibility_km: float,
) -> tuple[int, str]:
    """Return (score_contribution, normalised_condition_label).

    Score is 0–100 where higher = safer, matching the agent's convention.
    """
    cond_lower = condition.lower()

    if "thunder" in cond_lower:
        return 20, "Thunderstorm"
    if "heavy rain" in cond_lower or "torrential" in cond_lower:
        return 30, "Heavy Rain"
    if visibility_km < 2.0:
        return 30, f"{condition} (Low Visibility)"
    if "fog" in cond_lower or "mist" in cond_lower:
        return 50, "Fog / Mist"
    if wind_kph > 40.0:
        return 55, f"{condition} (Strong Winds)"
    if "rain" in cond_lower or "drizzle" in cond_lower or "shower" in cond_lower:
        return 60, "Rain"
    if "snow" in cond_lower or "blizzard" in cond_lower or "sleet" in cond_lower:
        return 40, "Snow / Ice"
    if "overcast" in cond_lower:
        return 75, "Overcast"
    if cond_lower == "cloudy":
        return 75, "Cloudy"
    # Clear, sunny, partly cloudy, etc. — preserve the original label
    return 85, condition


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

def _mock_weather(location: str) -> WeatherAnalysis:
    """Deterministic mock used when the API is unavailable."""
    import hashlib

    digest = int(hashlib.md5(location.lower().encode()).hexdigest(), 16)  # noqa: S324
    conditions = ["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Foggy", "Stormy"]
    scores =     [85,      75,       60,           30,           50,      20]
    idx = digest % len(conditions)
    return WeatherAnalysis(
        condition=conditions[idx],
        score_contribution=scores[idx],
        is_live=False,
    )


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def get_current_weather(location: str) -> WeatherAnalysis:
    """Fetch live weather for *location* and return a WeatherAnalysis.

    Falls back to mock data if:
      - WEATHER_API_KEY is not configured
      - The HTTP request fails or times out
      - The API returns a non-200 status
      - The response JSON is malformed
    """
    settings = get_settings()

    if not settings.WEATHER_API_KEY:
        logger.warning(
            "WEATHER_API_KEY not configured — using mock weather",
            location=location,
        )
        return _mock_weather(location)

    url = f"{_WEATHERAPI_BASE}/current.json"
    params = {"key": settings.WEATHER_API_KEY, "q": location, "aqi": "no"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)

        if response.status_code == 400:
            # WeatherAPI returns 400 for unrecognised locations
            logger.warning(
                "WeatherAPI: location not recognised — using mock weather",
                location=location,
                status=response.status_code,
            )
            return _mock_weather(location)

        response.raise_for_status()
        data = response.json()

        current = data["current"]
        raw_condition: str = current["condition"]["text"]
        temp_c: float = current["temp_c"]
        feels_like_c: float = current["feelslike_c"]
        humidity: int = current["humidity"]
        wind_kph: float = current["wind_kph"]
        visibility_km: float = current["vis_km"]

        score, normalised_condition = _evaluate_weather_risk(
            raw_condition, wind_kph, visibility_km
        )

        logger.info(
            "Live weather fetched",
            location=location,
            condition=normalised_condition,
            temp_c=temp_c,
            wind_kph=wind_kph,
            visibility_km=visibility_km,
            score=score,
        )

        return WeatherAnalysis(
            condition=normalised_condition,
            score_contribution=score,
            temperature_c=temp_c,
            feels_like_c=feels_like_c,
            humidity_pct=humidity,
            wind_kph=wind_kph,
            visibility_km=visibility_km,
            is_live=True,
        )

    except httpx.TimeoutException:
        logger.warning(
            "WeatherAPI request timed out — using mock weather",
            location=location,
            timeout=_TIMEOUT_SECONDS,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "WeatherAPI returned an error — using mock weather",
            location=location,
            status=exc.response.status_code,
        )
    except (httpx.RequestError, KeyError, ValueError) as exc:
        logger.warning(
            "WeatherAPI call failed — using mock weather",
            location=location,
            error=str(exc),
        )

    return _mock_weather(location)
