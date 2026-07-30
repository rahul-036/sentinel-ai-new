"""
Risk Assessment Agent — multi-route analysis.

Pipeline:
  1. Fetch primary route via get_route() (always reliable).
  2. Attempt fastest/shortest alternatives via route_optimization_service (bonus).
  3. Deduplicate by geometry fingerprint.
  4. For EACH route run Crime, Weather, Infrastructure, Traffic agents concurrently.
  5. Compute safety score per route. Mark safest as recommended.
  6. Return RiskAnalysisResponse with top-level fields from recommended route
     + routes list + recommended_index for the frontend switcher.

Score model (0-100, higher = safer):
  crime 40% | weather 20% | infrastructure 25% | traffic 15%
  Infra adjustment: Excellent +10 | Good +5 | Fair 0 | Poor -10
"""

import asyncio
import hashlib

import structlog

from app.agents.crime_agent import analyze_crime
from app.agents.emergency_response_agent import run_emergency_response
from app.agents.infrastructure_agent import analyze_infrastructure
from app.agents.prediction_agent import predict_incident
from app.agents.traffic_agent import TrafficAnalysisResult, analyze_traffic
from app.schemas.risk import (
    EmergencyServicesAnalysis,
    InfrastructureAnalysis,
    InfrastructureRating,
    LiveCrimeAnalysis,
    LiveInfrastructureAnalysis,
    RiskAnalysisResponse,
    RiskLevel,
    RiskRouteCoordinate,
    RiskRouteGeometry,
    RouteAnalysis,
    RouteOption,
    TrafficAnalysis,
    WeatherAnalysis,
)
from app.services.route_optimization_service import (
    RawRoute,
    RouteOptimizationServiceError,
    get_candidate_routes,
)
from app.services.route_service import RouteServiceError, get_route
from app.services.weather_service import get_current_weather

logger = structlog.get_logger(__name__)

_WEIGHTS: dict[str, float] = {
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

def _stable_int(seed: str, lo: int, hi: int) -> int:
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


def _compute_safety_score(
    crime_score: int,
    weather_score: int,
    infra_score: int,
    traffic_score: int,
    infra_rating: str,
) -> int:
    raw = (
        crime_score   * _WEIGHTS["crime"]
        + weather_score * _WEIGHTS["weather"]
        + infra_score   * _WEIGHTS["infrastructure"]
        + traffic_score * _WEIGHTS["traffic"]
    )
    return max(0, min(100, round(raw) + _INFRA_ADJUSTMENT.get(infra_rating, 0)))


def _fingerprint(coords: list[list[float]]) -> tuple:
    if not coords:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    n = len(coords)
    mid = coords[n // 2]
    return (coords[0][0], coords[0][1], mid[0], mid[1], coords[-1][0], coords[-1][1])


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class RiskAssessmentAgent:
    def __init__(self, source: str, destination: str) -> None:
        self.source = source.strip()
        self.destination = destination.strip()
        self._route_key = f"{self.source}|{self.destination}".lower()

    def analyze_emergency_services(self) -> EmergencyServicesAnalysis:
        police    = _stable_int(f"police:{self._route_key}",   lo=0, hi=5)
        hospitals = _stable_int(f"hospital:{self._route_key}", lo=0, hi=6)
        return EmergencyServicesAnalysis(
            nearby_police=police,
            nearby_hospitals=hospitals,
            score_contribution=min(100, (police * 10) + (hospitals * 8) + 20),
        )

    def analyze_infrastructure_mock(self) -> InfrastructureAnalysis:
        ratings: list[InfrastructureRating] = ["Poor", "Fair", "Good", "Excellent"]
        scores = [30, 55, 80, 95]
        idx = _stable_int(f"infra:{self._route_key}", lo=0, hi=len(ratings) - 1)
        return InfrastructureAnalysis(rating=ratings[idx], score_contribution=scores[idx])

    def _build_recommendation(self, safety_score: int, weather: WeatherAnalysis) -> tuple[str, str]:
        risk = _score_to_risk_level(safety_score)
        if risk == "Low":
            return (
                "Proceed via recommended route",
                f"The route from {self.source} to {self.destination} has low crime history, "
                f"{weather.condition.lower()} weather, adequate emergency services, and good infrastructure.",
            )
        if risk == "Medium":
            return (
                "Proceed with caution",
                f"The route has moderate risk factors. Weather is {weather.condition.lower()}. "
                "Stay alert and keep emergency contacts handy.",
            )
        if risk == "High":
            return (
                "Consider an alternative route",
                f"Elevated risk detected on the route from {self.source} to {self.destination}. "
                f"Weather: {weather.condition}. Avoid travel after dark if possible.",
            )
        return (
            "Avoid this route",
            f"Critical risk level detected. Conditions on the route from {self.source} "
            f"to {self.destination} are unsafe. Seek an alternative or delay travel.",
        )

    async def _score_route(
        self, raw: RawRoute
    ) -> tuple[RawRoute, LiveCrimeAnalysis, WeatherAnalysis, LiveInfrastructureAnalysis, TrafficAnalysisResult]:
        try:
            crime = analyze_crime(raw.coordinates)
            weather, infra, traffic = await asyncio.gather(
                get_current_weather(self.source),
                analyze_infrastructure(raw.coordinates),
                analyze_traffic(raw.coordinates),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Agent pipeline failed for route", preference=raw.preference, error=str(exc))
            crime = analyze_crime([])
            weather = await get_current_weather(self.source)
            infra = LiveInfrastructureAnalysis(rating="Unknown", score_contribution=40)
            traffic = TrafficAnalysisResult(
                traffic="Unknown", traffic_score=50, traffic_rating="Fair",
                congestion_percentage=0, average_speed_kph=0.0,
                free_flow_speed_kph=0.0, delay_minutes=0.0,
                incidents=0, traffic_live=False,
            )
        return raw, crime, weather, infra, traffic

    async def run(self) -> RiskAnalysisResponse:
        logger.info("Risk assessment started", source=self.source, destination=self.destination)

        # 1. Always fetch primary route first (reliable path)
        primary = await get_route(self.source, self.destination)
        primary_coords = [[c.lon, c.lat] for c in primary.geometry.coordinates]
        logger.info(
            "Primary route fetched",
            source=self.source,
            destination=self.destination,
            distance_km=primary.distance_km,
            duration_min=primary.duration_min,
            coords=len(primary_coords),
        )
        candidates: list[RawRoute] = [RawRoute(
            preference="recommended",
            distance_km=primary.distance_km or 0.0,
            duration_min=primary.duration_min or 0.0,
            coordinates=primary_coords,
        )]

        # 2. Attempt fastest + shortest alternatives
        try:
            alt_candidates = await get_candidate_routes(
                self.source, self.destination, preferences=["fastest", "shortest"]
            )
            seen = {_fingerprint(candidates[0].coordinates)}
            for c in alt_candidates:
                fp = _fingerprint(c.coordinates)
                if fp not in seen:
                    seen.add(fp)
                    candidates.append(c)
            logger.info("Alternative routes added", total_candidates=len(candidates))
        except Exception as exc:  # noqa: BLE001
            logger.info("Alternative routes unavailable — single route analysis", error=str(exc))

        # 3. Score all routes concurrently
        scored = await asyncio.gather(*[self._score_route(r) for r in candidates])

        # 4. Build RouteOption list, find best
        route_options: list[RouteOption] = []
        best_idx, best_score = 0, -1

        for i, (raw, crime, weather, infra, traffic) in enumerate(scored):
            score = _compute_safety_score(
                crime.score_contribution, weather.score_contribution,
                infra.score_contribution, traffic.traffic_score, infra.rating,
            )
            if score > best_score:
                best_score, best_idx = score, i
            route_options.append(RouteOption(
                route_index=i,
                preference=raw.preference,
                safety_score=score,
                risk_level=_score_to_risk_level(score),
                recommended=False,
                distance_km=raw.distance_km,
                duration_min=raw.duration_min,
                crime_risk=crime.crime_risk,
                weather=weather.condition,
                infrastructure=infra.rating,
                traffic=traffic.traffic,
                traffic_score=traffic.traffic_score,
                congestion_percentage=traffic.congestion_percentage,
                delay_minutes=traffic.delay_minutes,
                geometry=RiskRouteGeometry(
                    coordinates=[RiskRouteCoordinate(lon=c[0], lat=c[1]) for c in raw.coordinates]
                ) if raw.coordinates else None,
                crime_locations=crime.crime_locations,
            ))

        route_options[best_idx].recommended = True

        # 5. Top-level fields from recommended route
        best_raw, best_crime, best_weather, best_infra, best_traffic = scored[best_idx]
        route_live = bool(best_raw.coordinates)
        emergency_svc = self.analyze_emergency_services()
        recommendation, reason = self._build_recommendation(best_score, best_weather)

        logger.info(
            "Risk assessment complete",
            source=self.source, destination=self.destination,
            safety_score=best_score, routes=len(route_options), recommended_index=best_idx,
        )

        # 6. Run Prediction Agent
        prediction = predict_incident(
            safety_score=best_score,
            crime_risk=best_crime.crime_risk,
            nearby_crimes=best_crime.nearby_crimes,
            weather=best_weather.condition,
            wind_kph=best_weather.wind_kph,
            visibility_km=best_weather.visibility_km,
            congestion_pct=best_traffic.congestion_percentage,
            delay_minutes=best_traffic.delay_minutes,
            traffic_incidents=best_traffic.incidents,
            infra_rating=best_infra.rating,
            distance_km=best_raw.distance_km if route_live else None,
            duration_min=best_raw.duration_min if route_live else None,
        )

        # 7. Run Emergency Response Agent when risk is High or Critical
        risk_str = _score_to_risk_level(best_score)
        emergency_response = None
        if risk_str in ("High", "Critical"):
            try:
                emergency_response = run_emergency_response(
                    risk_level=risk_str,
                    route_coords=best_raw.coordinates,
                    facility_police=list(best_infra.facility_police),
                    facility_hospitals=list(best_infra.facility_hospitals),
                    facility_fire_stations=list(best_infra.facility_fire_stations),
                    average_speed_kph=best_traffic.average_speed_kph,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Emergency Response Agent failed", error=str(exc))

        return RiskAnalysisResponse(
            safety_score=best_score,
            risk_level=_score_to_risk_level(best_score),
            crime_risk=best_crime.crime_risk,
            recommendation=recommendation,
            reason=reason,
            nearby_crimes=best_crime.nearby_crimes,
            crime_locations=best_crime.crime_locations,
            weather=best_weather.condition,
            temperature_c=best_weather.temperature_c,
            feels_like_c=best_weather.feels_like_c,
            humidity_pct=best_weather.humidity_pct,
            wind_kph=best_weather.wind_kph,
            visibility_km=best_weather.visibility_km,
            weather_live=best_weather.is_live,
            nearby_police=best_infra.nearby_police if best_infra.is_live else emergency_svc.nearby_police,
            nearby_hospitals=best_infra.nearby_hospitals if best_infra.is_live else emergency_svc.nearby_hospitals,
            infrastructure=best_infra.rating,
            nearby_fire_stations=best_infra.nearby_fire_stations,
            nearby_petrol_pumps=best_infra.nearby_petrol_pumps,
            nearby_pharmacies=best_infra.nearby_pharmacies,
            nearby_metro_stations=best_infra.nearby_metro_stations,
            infrastructure_live=best_infra.is_live,
            facility_police=best_infra.facility_police,
            facility_hospitals=best_infra.facility_hospitals,
            facility_fire_stations=best_infra.facility_fire_stations,
            facility_petrol_pumps=best_infra.facility_petrol_pumps,
            facility_pharmacies=best_infra.facility_pharmacies,
            facility_metro_stations=best_infra.facility_metro_stations,
            traffic=best_traffic.traffic,
            traffic_score=best_traffic.traffic_score,
            traffic_rating=best_traffic.traffic_rating,
            congestion_percentage=best_traffic.congestion_percentage,
            average_speed_kph=best_traffic.average_speed_kph,
            free_flow_speed_kph=best_traffic.free_flow_speed_kph,
            delay_minutes=best_traffic.delay_minutes,
            traffic_incidents=best_traffic.incidents,
            traffic_live=best_traffic.traffic_live,
            source=self.source,
            destination=self.destination,
            distance_km=best_raw.distance_km if route_live else None,
            duration_min=best_raw.duration_min if route_live else None,
            geometry=RiskRouteGeometry(
                coordinates=[RiskRouteCoordinate(lon=c[0], lat=c[1]) for c in best_raw.coordinates]
            ) if route_live else None,
            route_live=route_live,
            routes=route_options,
            recommended_index=best_idx,
            prediction=prediction,
            emergency_response=emergency_response,
        )