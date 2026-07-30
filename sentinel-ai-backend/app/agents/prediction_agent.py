"""
AI Incident Prediction Agent.

Runs after Risk, Weather, Traffic, and Infrastructure agents have completed.
Combines their outputs to produce a forward-looking travel prediction — no
external API calls are made; all logic is deterministic rule-based inference.

Outputs (PredictionResponse):
  accident_probability      : Low | Medium | High
  traffic_delay_probability : Low | Medium | High
  crime_probability         : Low | Medium | High
  weather_impact            : Low | Moderate | High
  overall_future_risk       : Low | Medium | High
  recommended_departure     : str  (e.g. "Before 6:00 PM")
  ai_recommendation         : str  (human-readable advice)
"""

import structlog

from app.schemas.risk import PredictionLevel, PredictionResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _accident_probability(
    safety_score: int,
    congestion_pct: int,
    weather: str,
    infra_rating: str,
) -> PredictionLevel:
    score = 0
    if safety_score < 50:
        score += 2
    elif safety_score < 75:
        score += 1

    if congestion_pct >= 60:
        score += 2
    elif congestion_pct >= 30:
        score += 1

    if any(w in weather.lower() for w in ("rain", "storm", "fog", "snow", "hail", "thunder")):
        score += 2
    elif any(w in weather.lower() for w in ("cloud", "mist", "drizzle", "overcast")):
        score += 1

    if infra_rating in ("Poor",):
        score += 2
    elif infra_rating in ("Fair", "Unknown"):
        score += 1

    if score >= 5:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def _traffic_delay_probability(
    congestion_pct: int,
    delay_minutes: float,
    traffic_incidents: int,
) -> PredictionLevel:
    score = 0
    if congestion_pct >= 60:
        score += 2
    elif congestion_pct >= 30:
        score += 1

    if delay_minutes >= 15:
        score += 2
    elif delay_minutes >= 5:
        score += 1

    if traffic_incidents >= 3:
        score += 2
    elif traffic_incidents >= 1:
        score += 1

    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def _crime_probability(crime_risk: str, nearby_crimes: int) -> PredictionLevel:
    if crime_risk == "Critical" or nearby_crimes >= 7:
        return "High"
    if crime_risk == "High" or nearby_crimes >= 4:
        return "High"
    if crime_risk == "Medium" or nearby_crimes >= 1:
        return "Medium"
    return "Low"


def _weather_impact(weather: str, wind_kph: float | None, visibility_km: float | None) -> PredictionLevel:
    severe = ("storm", "thunder", "hail", "snow", "blizzard", "tornado")
    moderate = ("rain", "fog", "mist", "drizzle", "overcast", "cloud")

    w = weather.lower()
    if any(s in w for s in severe):
        return "High"
    if any(m in w for m in moderate):
        return "Moderate"
    if wind_kph is not None and wind_kph >= 50:
        return "High"
    if wind_kph is not None and wind_kph >= 25:
        return "Moderate"
    if visibility_km is not None and visibility_km < 1.0:
        return "High"
    if visibility_km is not None and visibility_km < 5.0:
        return "Moderate"
    return "Low"


def _overall_future_risk(
    accident: PredictionLevel,
    traffic_delay: PredictionLevel,
    crime: PredictionLevel,
    weather_imp: PredictionLevel,
    safety_score: int,
) -> PredictionLevel:
    _rank = {"Low": 0, "Moderate": 1, "Medium": 1, "High": 2}
    total = (
        _rank[accident]
        + _rank[traffic_delay]
        + _rank[crime]
        + _rank[weather_imp]
    )
    if total >= 6 or safety_score < 25:
        return "High"
    if total >= 3 or safety_score < 50:
        return "Medium"
    return "Low"


def _departure_time(
    congestion_pct: int,
    delay_minutes: float,
    overall: PredictionLevel,
) -> str:
    if overall == "High":
        return "Avoid travel — reschedule if possible"
    if congestion_pct >= 60 or delay_minutes >= 15:
        return "Before 7:00 AM or After 9:00 PM"
    if congestion_pct >= 30 or delay_minutes >= 5:
        return "Before 8:00 AM or After 8:00 PM"
    return "Any time — conditions are favourable"


def _build_recommendation(
    accident: PredictionLevel,
    traffic_delay: PredictionLevel,
    crime: PredictionLevel,
    weather_imp: PredictionLevel,
    overall: PredictionLevel,
    infra_rating: str,
) -> str:
    parts: list[str] = []

    if overall == "High":
        parts.append("High overall risk detected — consider postponing or choosing an alternative route.")
    elif overall == "Medium":
        parts.append("Moderate risk on this route — proceed with caution.")
    else:
        parts.append("Conditions look favourable for travel.")

    if traffic_delay == "High":
        parts.append("Expect significant traffic delays; leave well ahead of schedule.")
    elif traffic_delay == "Medium":
        parts.append("Some congestion expected — allow extra travel time.")

    if accident == "High":
        parts.append("Elevated accident risk — drive defensively and reduce speed.")
    elif accident == "Medium":
        parts.append("Moderate accident risk — stay alert.")

    if crime == "High":
        parts.append("High crime probability along this route — stay on well-lit main roads.")
    elif crime == "Medium":
        parts.append("Some crime activity nearby — keep valuables out of sight.")

    if weather_imp in ("High", "Moderate"):
        parts.append("Adverse weather may affect visibility and road grip — drive carefully.")

    if infra_rating == "Poor":
        parts.append("Poor road infrastructure — watch for potholes and uneven surfaces.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def predict_incident(
    safety_score: int,
    crime_risk: str,
    nearby_crimes: int,
    weather: str,
    wind_kph: float | None,
    visibility_km: float | None,
    congestion_pct: int,
    delay_minutes: float,
    traffic_incidents: int,
    infra_rating: str,
    distance_km: float | None,
    duration_min: float | None,
) -> PredictionResponse:
    """
    Pure rule-based prediction — never raises, never calls external services.
    All inputs come from agents that have already run.
    """
    accident      = _accident_probability(safety_score, congestion_pct, weather, infra_rating)
    traffic_delay = _traffic_delay_probability(congestion_pct, delay_minutes, traffic_incidents)
    crime         = _crime_probability(crime_risk, nearby_crimes)
    weather_imp   = _weather_impact(weather, wind_kph, visibility_km)
    overall       = _overall_future_risk(accident, traffic_delay, crime, weather_imp, safety_score)
    departure     = _departure_time(congestion_pct, delay_minutes, overall)
    recommendation = _build_recommendation(accident, traffic_delay, crime, weather_imp, overall, infra_rating)

    logger.info(
        "Prediction Agent complete",
        accident=accident,
        traffic_delay=traffic_delay,
        crime=crime,
        weather_impact=weather_imp,
        overall=overall,
        departure=departure,
    )

    return PredictionResponse(
        accident_probability=accident,
        traffic_delay_probability=traffic_delay,
        crime_probability=crime,
        weather_impact=weather_imp,
        overall_future_risk=overall,
        recommended_departure=departure,
        ai_recommendation=recommendation,
    )
