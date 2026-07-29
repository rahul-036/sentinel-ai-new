"""
Risk Assessment Agent.

Orchestrates all risk dimensions for a source → destination route by
calling sub-agents concurrently where possible and aggregating their
results into a single RiskAnalysisResponse.

Score model (0–100, higher = safer):
  crime          : 40 % weight
  weather        : 20 % weight
  emergency svcs : 15 % weight
  infrastructure : 25 % weight  (live, via InfrastructureAgent)

Infrastructure rating adjustment applied after weighted sum:
  Excellent → +10
  Good      → +5
  Fair      →  0
  Poor      → -10
  Unknown   →  0
"""

import asyncio
import hashlib

import structlog

from app.agents.infrastructure_agent import analyze_infrastructure
from app.schemas.risk import (
    CrimeAnalysis,
    EmergencyServicesAnalysis,
    InfrastructureAnalysis,
    InfrastructureRating,
    LiveInfrastructureAnalysis,
    RiskAnalysisResponse,
    RiskLevel,
    RiskRouteCoordinate,
    RiskRouteGeometry,
    RouteAnalysis,
    WeatherAnalysis,
)
from app.services.route_service import RouteServiceError, get_route
from app.services.weather_service import get_current_weather

logger = structlog.get_logger(__name__)

_WEIGHTS: dict[str, float] = {
    "crime":          0.40,
    "weather":        0.20,
    "emergency":      0.15,
    "infrastructure": 0.25,
}

_INFRA_ADJUSTMENT: dict[str, int] = {
    "Excellent": +10,
    "Good":      +5,
    "Fair":       0,
    "Poor":      -10,
    "Unknown":    0,
}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _stable_int(seed: str, lo: int, hi: int) -> int:
    """Deterministic int derived from a string seed via MD5.

    Keeps responses consistent for the same source/destination pair
    without a database, making manual testing predictable.
    """
    digest = int(hashlib.md5(seed.encode()).hexdigest(), 16)  # noqa: S324
    return lo + (digest % (hi - lo + 1))


def _score_to_risk_level(score: int) -> RiskLevel:
    if score >= 75:
        return "Low"
    if score >= 50:
        return "Medium"
    if score >= 25:
        return "High"
    return "Critical"


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class RiskAssessmentAgent:
    """Orchestrates all risk dimensions for a source → destination route."""

    def __init__(self, source: str, destination: str) -> None:
        self.source = source.strip()
        self.destination = destination.strip()
        self._route_key = f"{self.source}|{self.destination}".lower()

    # ------------------------------------------------------------------
    # Sub-agent methods
    # ------------------------------------------------------------------

    def analyze_crime(self) -> CrimeAnalysis:
        """Return crime risk for the route (mock — replace with live API later)."""
        score = _stable_int(f"crime:{self._route_key}", lo=40, hi=95)
        risk = _score_to_risk_level(score)
        logger.debug("Crime analysis complete", route=self._route_key, score=score, risk=risk)
        return CrimeAnalysis(crime_risk=risk, score_contribution=score)

    async def analyze_route(self) -> RouteAnalysis:
        """Fetch live route data from the Route Agent (ORS).

        Returns a RouteAnalysis with distance, duration, and the full
        coordinate list. On any ORS failure logs a warning and returns
        a zero-distance fallback so the rest of the pipeline is unaffected.

        The `coordinates` list is the shared input for all geo-aware sub-agents:
          - InfrastructureAgent → Overpass facility queries per segment
          - CrimeAgent          → crime stats along each coordinate (future)
          - TrafficAgent        → live congestion per segment (future)
        """
        try:
            result = await get_route(self.source, self.destination)
            coords = [[c.lon, c.lat] for c in result.geometry.coordinates]
            logger.debug(
                "Route analysis complete",
                route=self._route_key,
                distance_km=result.distance_km,
                duration_min=result.duration_min,
                total_points=len(coords),
            )
            return RouteAnalysis(
                distance_km=result.distance_km,
                duration_min=result.duration_min,
                coordinates=coords,
                is_live=True,
            )
        except RouteServiceError as exc:
            logger.warning(
                "Route Agent unavailable — continuing without route data",
                route=self._route_key,
                error=str(exc),
            )
            return RouteAnalysis(distance_km=0.0, duration_min=0.0, is_live=False)

    async def analyze_weather(self) -> WeatherAnalysis:
        """Return current weather conditions for the route.

        Calls WeatherAPI.com using the source location as the query.
        Falls back to deterministic mock data if the API is unavailable.
        """
        weather = await get_current_weather(self.source)
        logger.debug(
            "Weather analysis complete",
            route=self._route_key,
            condition=weather.condition,
            score=weather.score_contribution,
            live=weather.is_live,
        )
        return weather

    def analyze_emergency_services(self) -> EmergencyServicesAnalysis:
        """Return nearby emergency service counts (mock — replace with live API later)."""
        police = _stable_int(f"police:{self._route_key}", lo=0, hi=5)
        hospitals = _stable_int(f"hospital:{self._route_key}", lo=0, hi=6)
        score = min(100, (police * 10) + (hospitals * 8) + 20)
        logger.debug(
            "Emergency services analysis complete",
            route=self._route_key,
            police=police,
            hospitals=hospitals,
        )
        return EmergencyServicesAnalysis(
            nearby_police=police,
            nearby_hospitals=hospitals,
            score_contribution=score,
        )

    def analyze_infrastructure_mock(self) -> InfrastructureAnalysis:
        """Mock infrastructure rating — kept for backward compatibility.

        Not called by run(); superseded by the live InfrastructureAgent.
        Can be used in unit tests that do not require Overpass connectivity.
        """
        ratings: list[InfrastructureRating] = ["Poor", "Fair", "Good", "Excellent"]
        scores = [30, 55, 80, 95]
        idx = _stable_int(f"infra:{self._route_key}", lo=0, hi=len(ratings) - 1)
        logger.debug(
            "Infrastructure mock analysis complete",
            route=self._route_key,
            rating=ratings[idx],
        )
        return InfrastructureAnalysis(rating=ratings[idx], score_contribution=scores[idx])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_recommendation(
        self, safety_score: int, weather: WeatherAnalysis
    ) -> tuple[str, str]:
        risk = _score_to_risk_level(safety_score)
        if risk == "Low":
            rec = "Proceed via recommended route"
            reason = (
                f"The route from {self.source} to {self.destination} has low crime history, "
                f"{weather.condition.lower()} weather, adequate emergency services, "
                "and good infrastructure."
            )
        elif risk == "Medium":
            rec = "Proceed with caution"
            reason = (
                f"The route has moderate risk factors. Weather is {weather.condition.lower()}. "
                "Stay alert and keep emergency contacts handy."
            )
        elif risk == "High":
            rec = "Consider an alternative route"
            reason = (
                f"Elevated risk detected on the route from {self.source} to {self.destination}. "
                f"Weather: {weather.condition}. Avoid travel after dark if possible."
            )
        else:
            rec = "Avoid this route"
            reason = (
                f"Critical risk level detected. Conditions on the route from {self.source} "
                f"to {self.destination} are unsafe. Seek an alternative or delay travel."
            )
        return rec, reason

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    async def run(self) -> RiskAnalysisResponse:
        """Execute all analysis methods and return the consolidated response."""
        logger.info("Risk assessment started", source=self.source, destination=self.destination)

        # Route Agent runs first — its coordinates are the shared input for
        # all geo-aware sub-agents (Infrastructure, Crime, Traffic).
        route = await self.analyze_route()

        # Weather and Infrastructure have no dependency on each other —
        # run them concurrently to minimise total wall-clock latency.
        weather, infra = await asyncio.gather(
            self.analyze_weather(),
            analyze_infrastructure(route.coordinates),
        )

        # Synchronous sub-agents — no I/O, run inline.
        crime = self.analyze_crime()
        emergency = self.analyze_emergency_services()

        # Weighted base score
        raw_score = (
            crime.score_contribution      * _WEIGHTS["crime"]
            + weather.score_contribution  * _WEIGHTS["weather"]
            + emergency.score_contribution * _WEIGHTS["emergency"]
            + infra.score_contribution    * _WEIGHTS["infrastructure"]
        )

        # Infrastructure quality adjustment — clamped to 0–100
        adjustment = _INFRA_ADJUSTMENT.get(infra.rating, 0)
        safety_score = max(0, min(100, round(raw_score) + adjustment))

        recommendation, reason = self._build_recommendation(safety_score, weather)

        logger.info(
            "Risk assessment complete",
            source=self.source,
            destination=self.destination,
            safety_score=safety_score,
            risk_level=_score_to_risk_level(safety_score),
            weather_live=weather.is_live,
            route_live=route.is_live,
            infrastructure_live=infra.is_live,
            infrastructure_rating=infra.rating,
        )

        return RiskAnalysisResponse(
            # ── Core ──────────────────────────────────────────────────────────
            safety_score=safety_score,
            risk_level=_score_to_risk_level(safety_score),
            crime_risk=crime.crime_risk,
            recommendation=recommendation,
            reason=reason,
            # ── Weather ───────────────────────────────────────────────────────
            weather=weather.condition,
            temperature_c=weather.temperature_c,
            feels_like_c=weather.feels_like_c,
            humidity_pct=weather.humidity_pct,
            wind_kph=weather.wind_kph,
            visibility_km=weather.visibility_km,
            weather_live=weather.is_live,
            # ── Emergency services ─────────────────────────────────────────
            # Prefer live Overpass counts when available; fall back to mock.
            nearby_police=infra.nearby_police if infra.is_live else emergency.nearby_police,
            nearby_hospitals=infra.nearby_hospitals if infra.is_live else emergency.nearby_hospitals,
            # ── Infrastructure (live) ─────────────────────────────────────────
            infrastructure=infra.rating,
            nearby_fire_stations=infra.nearby_fire_stations,
            nearby_petrol_pumps=infra.nearby_petrol_pumps,
            nearby_pharmacies=infra.nearby_pharmacies,
            nearby_metro_stations=infra.nearby_metro_stations,
            infrastructure_live=infra.is_live,
            facility_police=infra.facility_police,
            facility_hospitals=infra.facility_hospitals,
            facility_fire_stations=infra.facility_fire_stations,
            facility_petrol_pumps=infra.facility_petrol_pumps,
            facility_pharmacies=infra.facility_pharmacies,
            facility_metro_stations=infra.facility_metro_stations,
            # ── Route ─────────────────────────────────────────────────────────
            source=self.source,
            destination=self.destination,
            distance_km=route.distance_km if route.is_live else None,
            duration_min=route.duration_min if route.is_live else None,
            geometry=RiskRouteGeometry(
                coordinates=[
                    RiskRouteCoordinate(lon=c[0], lat=c[1])
                    for c in route.coordinates
                ]
            ) if route.is_live else None,
            route_live=route.is_live,
        )
