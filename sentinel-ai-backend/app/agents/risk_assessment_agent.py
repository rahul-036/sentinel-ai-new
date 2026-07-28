"""
Risk Assessment Agent — Phase 1 (mock data).

Each public method maps to a future sub-agent that will call real data
sources (crime APIs, weather APIs, maps, etc.).  The interface between
methods is typed via the intermediate schemas in app/schemas/risk.py so
the swap-in will be a one-method-at-a-time replacement with no structural
changes required.

Score model (0–100, higher = safer):
  crime          : 40 % weight
  weather        : 20 % weight
  emergency svcs : 25 % weight
  infrastructure : 15 % weight
"""

import hashlib

import structlog

from app.schemas.risk import (
    CrimeAnalysis,
    EmergencyServicesAnalysis,
    InfrastructureAnalysis,
    InfrastructureRating,
    RiskAnalysisResponse,
    RiskLevel,
    WeatherAnalysis,
)
from app.services.weather_service import get_current_weather

logger = structlog.get_logger(__name__)

_WEIGHTS: dict[str, float] = {
    "crime": 0.40,
    "weather": 0.20,
    "emergency": 0.25,
    "infrastructure": 0.15,
}


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


class RiskAssessmentAgent:
    """Orchestrates all risk dimensions for a source → destination route."""

    def __init__(self, source: str, destination: str) -> None:
        self.source = source.strip()
        self.destination = destination.strip()
        self._route_key = f"{self.source}|{self.destination}".lower()

    # ------------------------------------------------------------------
    # Sub-agent methods (mock — replace one at a time in later phases)
    # ------------------------------------------------------------------

    def analyze_crime(self) -> CrimeAnalysis:
        """Return crime risk for the route.

        Future: query a crime-statistics API or a fine-tuned LLM tool.
        """
        score = _stable_int(f"crime:{self._route_key}", lo=40, hi=95)
        risk = _score_to_risk_level(score)
        logger.debug("Crime analysis complete", route=self._route_key, score=score, risk=risk)
        return CrimeAnalysis(crime_risk=risk, score_contribution=score)

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
        """Return nearby emergency service counts.

        Future: query a places/maps API within a configurable radius.
        """
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

    def analyze_infrastructure(self) -> InfrastructureAnalysis:
        """Return road/infrastructure quality rating.

        Future: integrate road-quality datasets or satellite imagery models.
        """
        ratings: list[InfrastructureRating] = ["Poor", "Fair", "Good", "Excellent"]
        scores = [30, 55, 80, 95]
        idx = _stable_int(f"infra:{self._route_key}", lo=0, hi=len(ratings) - 1)
        logger.debug(
            "Infrastructure analysis complete",
            route=self._route_key,
            rating=ratings[idx],
        )
        return InfrastructureAnalysis(rating=ratings[idx], score_contribution=scores[idx])

    def calculate_safety_score(
        self,
        crime: CrimeAnalysis,
        weather: WeatherAnalysis,
        emergency: EmergencyServicesAnalysis,
        infrastructure: InfrastructureAnalysis,
    ) -> int:
        """Weighted aggregation of all sub-scores into a single 0–100 safety score."""
        raw = (
            crime.score_contribution * _WEIGHTS["crime"]
            + weather.score_contribution * _WEIGHTS["weather"]
            + emergency.score_contribution * _WEIGHTS["emergency"]
            + infrastructure.score_contribution * _WEIGHTS["infrastructure"]
        )
        return round(raw)

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

        crime = self.analyze_crime()
        weather = await self.analyze_weather()          # async — live API call
        emergency = self.analyze_emergency_services()
        infrastructure = self.analyze_infrastructure()
        safety_score = self.calculate_safety_score(crime, weather, emergency, infrastructure)
        recommendation, reason = self._build_recommendation(safety_score, weather)

        logger.info(
            "Risk assessment complete",
            source=self.source,
            destination=self.destination,
            safety_score=safety_score,
            risk_level=_score_to_risk_level(safety_score),
            weather_live=weather.is_live,
        )

        return RiskAnalysisResponse(
            safety_score=safety_score,
            risk_level=_score_to_risk_level(safety_score),
            crime_risk=crime.crime_risk,
            weather=weather.condition,
            temperature_c=weather.temperature_c,
            feels_like_c=weather.feels_like_c,
            humidity_pct=weather.humidity_pct,
            wind_kph=weather.wind_kph,
            visibility_km=weather.visibility_km,
            weather_live=weather.is_live,
            nearby_police=emergency.nearby_police,
            nearby_hospitals=emergency.nearby_hospitals,
            infrastructure=infrastructure.rating,
            recommendation=recommendation,
            reason=reason,
        )
