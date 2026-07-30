"""
TrafficAgent — evaluates live traffic conditions along a route.

Scoring model (0–100, higher = better / less congested):
  Base score    : 100 - congestion_percentage
  Incident penalty : -10 per incident, capped at -30
  Confidence blend : when TomTom confidence < 1.0 the score is blended
                     toward 50 to reflect data uncertainty

Traffic rating thresholds:
  80–100 → Excellent
  60–79  → Good
  40–59  → Fair
  0–39   → Poor

Traffic condition labels:
  congestion < 20 % → Light
  congestion < 50 % → Moderate
  congestion < 75 % → Heavy
  congestion ≥ 75 % → Severe

Fallback (traffic="Unknown", score=50, rating="Fair", is_live=False) is
returned ONLY when TomTom is genuinely unreachable or the API key is missing.
Every fallback path logs the exact reason.
"""

from dataclasses import dataclass

import structlog

from app.services.traffic_service import (
    TrafficData,
    TrafficServiceError,
    get_traffic_along_route,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Public data structure (returned to the caller / Risk Assessment Agent)
# ---------------------------------------------------------------------------

@dataclass
class TrafficAnalysisResult:
    traffic: str
    traffic_score: int
    traffic_rating: str
    congestion_percentage: int
    average_speed_kph: float
    free_flow_speed_kph: float
    delay_minutes: float
    incidents: int
    traffic_live: bool


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _calculate_score(data: TrafficData) -> int:
    base = max(0, 100 - data.congestion_percentage)
    incident_penalty = min(30, data.incidents * 10)
    raw = base - incident_penalty
    # Blend toward neutral (50) when TomTom confidence is low
    blended = data.confidence * raw + (1 - data.confidence) * 50
    return max(0, min(100, round(blended)))


def _score_to_rating(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Poor"


def _congestion_to_label(congestion_pct: int) -> str:
    if congestion_pct < 20:
        return "Light"
    if congestion_pct < 50:
        return "Moderate"
    if congestion_pct < 75:
        return "Heavy"
    return "Severe"


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def _fallback(reason: str) -> TrafficAnalysisResult:
    """Return a neutral fallback and log exactly why it was triggered."""
    logger.warning(
        "Traffic Agent using fallback",
        reason=reason,
        traffic="Unknown",
        score=50,
        rating="Fair",
    )
    return TrafficAnalysisResult(
        traffic="Unknown",
        traffic_score=50,
        traffic_rating="Fair",
        congestion_percentage=0,
        average_speed_kph=0.0,
        free_flow_speed_kph=0.0,
        delay_minutes=0.0,
        incidents=0,
        traffic_live=False,
    )


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def analyze_traffic(
    coordinates: list[list[float]],
) -> TrafficAnalysisResult:
    """
    Fetch live TomTom traffic data for the route and return a scored result.
    Never raises — every error path returns _fallback() with a logged reason.
    """
    if not coordinates:
        return _fallback("No coordinates received (list is empty)")

    logger.info(
        "Traffic Agent started",
        coordinate_count=len(coordinates),
        first_coord=coordinates[0],
        last_coord=coordinates[-1],
    )

    try:
        data: TrafficData = await get_traffic_along_route(coordinates)
    except TrafficServiceError as exc:
        return _fallback(f"TrafficServiceError: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _fallback(
            f"Unexpected exception from TrafficService: {type(exc).__name__}: {exc}"
        )

    score = _calculate_score(data)
    rating = _score_to_rating(score)
    condition = _congestion_to_label(data.congestion_percentage)

    logger.info(
        "Traffic Agent complete — live result",
        traffic=condition,
        score=score,
        rating=rating,
        congestion_pct=data.congestion_percentage,
        avg_speed_kph=data.average_speed_kph,
        free_flow_kph=data.free_flow_speed_kph,
        delay_min=data.delay_minutes,
        incidents=data.incidents,
        confidence=data.confidence,
    )

    return TrafficAnalysisResult(
        traffic=condition,
        traffic_score=score,
        traffic_rating=rating,
        congestion_percentage=data.congestion_percentage,
        average_speed_kph=data.average_speed_kph,
        free_flow_speed_kph=data.free_flow_speed_kph,
        delay_minutes=data.delay_minutes,
        incidents=data.incidents,
        traffic_live=data.is_live,
    )
