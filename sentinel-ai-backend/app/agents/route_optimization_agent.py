"""
Route Optimization Agent.

For each candidate route returned by RouteOptimizationService:
  1. Run Crime, Weather, Infrastructure, and Traffic agents concurrently.
  2. Compute a composite safety score using the same weights as
     RiskAssessmentAgent (crime 40 %, weather 20 %, infra 25 %, traffic 15 %).
  3. Mark the route with the highest safety score as recommended=True.
  4. Return a RouteOptimizationResponse with all routes ranked.

Reuses existing agents — no logic is duplicated.
"""

import asyncio

import structlog

from app.agents.crime_agent import analyze_crime
from app.agents.infrastructure_agent import analyze_infrastructure
from app.agents.traffic_agent import analyze_traffic
from app.schemas.risk import (
    InfrastructureRating,
    RiskLevel,
    RiskRouteCoordinate,
    RiskRouteGeometry,
    RouteOptimizationResponse,
    RouteOption,
)
from app.services.route_optimization_service import (
    RawRoute,
    RouteOptimizationServiceError,
    get_candidate_routes,
)
from app.services.route_service import RouteServiceError
from app.services.weather_service import get_current_weather

logger = structlog.get_logger(__name__)

# Weights must sum to 1.0
_WEIGHTS = {
    "crime":          0.40,
    "weather":        0.20,
    "infrastructure": 0.25,
    "traffic":        0.15,
}

_INFRA_ADJUSTMENT: dict[str, int] = {
    "Excellent": +10,
    "Good":      +5,
    "Fair":       0,
    "Poor":      -10,
    "Unknown":    0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_to_risk(score: int) -> RiskLevel:
    if score >= 75:
        return "Low"
    if score >= 50:
        return "Medium"
    if score >= 25:
        return "High"
    return "Critical"


async def _score_route(
    route: RawRoute,
    source: str,
) -> tuple[int, RouteOption]:
    """Run all sub-agents for one route and return (safety_score, RouteOption)."""
    coords = route.coordinates

    crime, weather, infra, traffic = await asyncio.gather(
        asyncio.to_thread(analyze_crime, coords),
        get_current_weather(source),
        analyze_infrastructure(coords),
        analyze_traffic(coords),
    )

    raw = (
        crime.score_contribution   * _WEIGHTS["crime"]
        + weather.score_contribution * _WEIGHTS["weather"]
        + infra.score_contribution   * _WEIGHTS["infrastructure"]
        + traffic.traffic_score      * _WEIGHTS["traffic"]
    )
    adjustment = _INFRA_ADJUSTMENT.get(infra.rating, 0)
    safety_score = max(0, min(100, round(raw) + adjustment))

    geometry = RiskRouteGeometry(
        coordinates=[RiskRouteCoordinate(lon=c[0], lat=c[1]) for c in coords]
    )

    option = RouteOption(
        route_index=0,          # filled in by caller
        preference=route.preference,
        safety_score=safety_score,
        risk_level=_score_to_risk(safety_score),
        recommended=False,      # set after comparing all routes
        distance_km=route.distance_km,
        duration_min=route.duration_min,
        crime_risk=crime.crime_risk,
        weather=weather.condition,
        infrastructure=infra.rating,
        traffic=traffic.traffic,
        traffic_score=traffic.traffic_score,
        congestion_percentage=traffic.congestion_percentage,
        delay_minutes=traffic.delay_minutes,
        geometry=geometry,
        crime_locations=crime.crime_locations,
    )
    return safety_score, option


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def optimize_route(
    source: str,
    destination: str,
) -> RouteOptimizationResponse:
    """
    Fetch candidate routes and score each one.
    Returns a RouteOptimizationResponse with the safest route marked recommended
    and the fastest route identified separately.
    Raises RouteServiceError if geocoding fails — endpoint handles it.
    """
    logger.info("Route Optimization Agent started", source=source, destination=destination)

    # RouteServiceError (geocoding failure) is intentionally NOT caught here —
    # it propagates to the endpoint which returns a 422 with a friendly message.
    candidates: list[RawRoute] = await get_candidate_routes(source, destination)

    # Log coordinates sent to ORS for each candidate
    for c in candidates:
        logger.info(
            "Candidate route coordinates",
            preference=c.preference,
            first_coord=c.coordinates[0] if c.coordinates else None,
            last_coord=c.coordinates[-1] if c.coordinates else None,
            total_points=len(c.coordinates),
            distance_km=c.distance_km,
            duration_min=c.duration_min,
        )

    # Score all routes concurrently
    scored = await asyncio.gather(*[_score_route(r, source) for r in candidates])

    # Assign indices, find safest (highest safety score) and fastest (lowest duration)
    options: list[RouteOption] = []
    best_safety_idx = 0
    best_safety_score = -1
    fastest_idx = 0
    min_duration = float("inf")

    for i, (score, option) in enumerate(scored):
        option.route_index = i
        options.append(option)
        if score > best_safety_score:
            best_safety_score = score
            best_safety_idx = i
        if option.duration_min < min_duration:
            min_duration = option.duration_min
            fastest_idx = i

    options[best_safety_idx].recommended = True

    logger.info(
        "Route Optimization Agent complete",
        routes=len(options),
        recommended_index=best_safety_idx,
        best_safety_score=best_safety_score,
        fastest_index=fastest_idx,
        fastest_duration_min=min_duration,
        safest_and_fastest_differ=(best_safety_idx != fastest_idx),
    )

    return RouteOptimizationResponse(
        source=source,
        destination=destination,
        routes=options,
        recommended_index=best_safety_idx,
        fastest_index=fastest_idx,
    )
