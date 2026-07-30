"""
Crime Intelligence Agent.

Receives route coordinates from the Route Agent, calls CrimeService to
find nearby crime areas via geospatial proximity, and returns a scored
CrimeAnalysisResult consumed by the Risk Assessment Agent.

Scoring model (score_contribution: 0–100, higher = safer):

  Base score by nearby crime count:
    0 areas          → 90  (Low)
    1–3 areas        → 65  (Medium)
    4–6 areas        → 40  (High)
    7+ areas         → 15  (Critical)

  Severity penalty applied per matched area:
    Risk Level "Low"    → −5
    Risk Level "Medium" → −10
    Risk Level "High"   → −20

  Final score is clamped to [0, 100].

crime_risk thresholds (derived from final score):
    score ≥ 75  → Low
    score ≥ 50  → Medium
    score ≥ 25  → High
    score < 25  → Critical
"""

from __future__ import annotations

import structlog

from app.schemas.risk import CrimeLocationDetail, LiveCrimeAnalysis
from app.services.crime_service import CrimeLocation, get_crimes_near_route

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

_BASE_SCORES: list[tuple[int, int]] = [
    # (max_count_inclusive, base_score)  — evaluated top-to-bottom
    (0, 90),
    (3, 65),
    (6, 40),
]
_BASE_SCORE_CRITICAL = 15

_SEVERITY_PENALTY: dict[str, int] = {
    "Low":    5,
    "Medium": 10,
    "High":   20,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_score(count: int) -> int:
    for max_count, score in _BASE_SCORES:
        if count <= max_count:
            return score
    return _BASE_SCORE_CRITICAL


def _score_to_risk(score: int) -> str:
    if score >= 75:
        return "Low"
    if score >= 50:
        return "Medium"
    if score >= 25:
        return "High"
    return "Critical"


def _calculate_score(nearby: list[CrimeLocation]) -> int:
    score = _base_score(len(nearby))
    for loc in nearby:
        score -= _SEVERITY_PENALTY.get(loc.risk_level, 0)
    return max(0, min(100, score))


def _to_detail(loc: CrimeLocation) -> CrimeLocationDetail:
    return CrimeLocationDetail(
        area=loc.area,
        crime_index=loc.crime_index,
        risk_level=loc.risk_level,
        latitude=loc.latitude,
        longitude=loc.longitude,
        dominant_crime_type=loc.dominant_crime_type,
        distance_m=loc.distance_m,
    )


# ---------------------------------------------------------------------------
# Public agent function
# ---------------------------------------------------------------------------


def analyze_crime(route_coords: list[list[float]]) -> LiveCrimeAnalysis:
    """
    Run the Crime Intelligence Agent for the given route coordinates.

    Args:
        route_coords: Ordered [[lon, lat], ...] pairs from the Route Agent.
                      Pass an empty list when the Route Agent is unavailable —
                      the agent returns a safe fallback (score=50, risk=Medium).

    Returns:
        LiveCrimeAnalysis — never raises.
    """
    # ── Fallback when route is unavailable ──────────────────────────────────
    if not route_coords:
        logger.warning("Crime Agent: no route coordinates — returning fallback")
        return LiveCrimeAnalysis(
            crime_risk="Medium",
            nearby_crimes=0,
            score_contribution=50,
            crime_locations=[],
            is_live=False,
        )

    # ── Geospatial proximity query ───────────────────────────────────────────
    try:
        nearby = get_crimes_near_route(route_coords)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Crime Agent: service error — returning fallback", error=str(exc))
        return LiveCrimeAnalysis(
            crime_risk="Medium",
            nearby_crimes=0,
            score_contribution=50,
            crime_locations=[],
            is_live=False,
        )

    # ── Score and classify ───────────────────────────────────────────────────
    score = _calculate_score(nearby)
    risk = _score_to_risk(score)

    logger.info(
        "Crime Agent complete",
        route_points=len(route_coords),
        nearby_areas=len(nearby),
        score=score,
        risk=risk,
    )

    return LiveCrimeAnalysis(
        crime_risk=risk,
        nearby_crimes=len(nearby),
        score_contribution=score,
        crime_locations=[_to_detail(loc) for loc in nearby],
        is_live=True,
    )
