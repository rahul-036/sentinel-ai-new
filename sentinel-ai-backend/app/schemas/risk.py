from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Literal type aliases
# ---------------------------------------------------------------------------

RiskLevel = Literal["Low", "Medium", "High", "Critical"]
InfrastructureRating = Literal["Poor", "Fair", "Good", "Excellent", "Unknown"]
PredictionLevel = Literal["Low", "Medium", "High", "Moderate"]


# ---------------------------------------------------------------------------
# Prediction schema
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    """Output of the AI Incident Prediction Agent."""
    accident_probability: PredictionLevel
    traffic_delay_probability: PredictionLevel
    crime_probability: PredictionLevel
    weather_impact: PredictionLevel
    overall_future_risk: PredictionLevel
    recommended_departure: str
    ai_recommendation: str


# ---------------------------------------------------------------------------
# Emergency Response schemas
# ---------------------------------------------------------------------------

class EmergencyFacilityInfo(BaseModel):
    """One nearest emergency facility with ETA."""
    name: str
    distance_km: Optional[float] = None
    eta_minutes: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    available: bool = False


class EmergencyResponseResult(BaseModel):
    """Output of the Emergency Response Agent."""
    activated: bool = False
    trigger_reason: str = ""
    nearest_police: EmergencyFacilityInfo
    nearest_hospital: EmergencyFacilityInfo
    nearest_fire_station: EmergencyFacilityInfo
    emergency_contacts: dict[str, str] = Field(default_factory=dict)
    status: str = "Standby"


# ---------------------------------------------------------------------------
# Request schema — standalone class, no import from route.py
# Keeps the OpenAPI component name "RiskAnalysisRequest" independent of
# "RouteAnalysisRequest" so there is zero name collision in components/schemas.
# ---------------------------------------------------------------------------

class RiskAnalysisRequest(BaseModel):
    source: str = Field(..., min_length=1, examples=["Hyderabad"])
    destination: str = Field(..., min_length=1, examples=["Gachibowli"])


# ---------------------------------------------------------------------------
# Nested geometry — prefixed to avoid collision with RouteGeometry in route.py
# ---------------------------------------------------------------------------

class RiskRouteCoordinate(BaseModel):
    lon: float
    lat: float


class RiskRouteGeometry(BaseModel):
    coordinates: list[RiskRouteCoordinate]


# ---------------------------------------------------------------------------
# Facility detail — one entry per deduplicated OSM element
# ---------------------------------------------------------------------------

class FacilityDetail(BaseModel):
    id: str = Field(..., description="Unique OSM element identifier (type:id)")
    name: str = Field("", description="Facility name from OSM tags, empty string if unnamed")
    type: str = Field(
        ...,
        description=(
            "Normalised facility type: police | hospital | fire_station "
            "| petrol_pump | pharmacy | metro_station"
        ),
    )
    latitude: float
    longitude: float


# ---------------------------------------------------------------------------
# Public response schema
# ---------------------------------------------------------------------------

class CrimeLocationDetail(BaseModel):
    """One crime area near the route — for Leaflet map markers."""

    area: str
    crime_index: int
    risk_level: RiskLevel
    latitude: float
    longitude: float
    dominant_crime_type: str
    distance_m: float = Field(..., description="Shortest distance to the route in metres")


class RiskAnalysisResponse(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────────
    safety_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    crime_risk: RiskLevel
    weather: str
    nearby_police: int = Field(..., ge=0)
    nearby_hospitals: int = Field(..., ge=0)
    infrastructure: InfrastructureRating
    recommendation: str
    reason: str
    # ── Crime intelligence ────────────────────────────────────────────────────
    nearby_crimes: int = Field(default=0, ge=0)
    crime_locations: list[CrimeLocationDetail] = Field(default_factory=list)
    # ── Weather detail ────────────────────────────────────────────────────────
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_pct: Optional[int] = None
    wind_kph: Optional[float] = None
    visibility_km: Optional[float] = None
    weather_live: bool = False
    # ── Route data ────────────────────────────────────────────────────────────
    source: Optional[str] = None
    destination: Optional[str] = None
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None
    geometry: Optional[RiskRouteGeometry] = None
    route_live: bool = False
    # ── Infrastructure counts ─────────────────────────────────────────────────
    nearby_fire_stations: int = 0
    nearby_petrol_pumps: int = 0
    nearby_pharmacies: int = 0
    nearby_metro_stations: int = 0
    infrastructure_live: bool = False
    # ── Facility detail lists — for Leaflet map markers ───────────────────────
    facility_police: list[FacilityDetail] = Field(default_factory=list)
    facility_hospitals: list[FacilityDetail] = Field(default_factory=list)
    facility_fire_stations: list[FacilityDetail] = Field(default_factory=list)
    facility_petrol_pumps: list[FacilityDetail] = Field(default_factory=list)
    facility_pharmacies: list[FacilityDetail] = Field(default_factory=list)
    facility_metro_stations: list[FacilityDetail] = Field(default_factory=list)
    # ── Traffic intelligence ─────────────────────────────────────────────────────
    traffic: str = "Unknown"
    traffic_score: int = 50
    traffic_rating: str = "Fair"
    congestion_percentage: int = 0
    average_speed_kph: float = 0.0
    free_flow_speed_kph: float = 0.0
    delay_minutes: float = 0.0
    traffic_incidents: int = 0
    traffic_live: bool = False
    # ── Multi-route comparison ────────────────────────────────────────────────
    routes: list["RouteOption"] = Field(default_factory=list)
    recommended_index: int = 0
    # ── Incident Prediction ───────────────────────────────────────────────────
    prediction: Optional["PredictionResponse"] = None
    # ── Emergency Response ───────────────────────────────────────────────────
    emergency_response: Optional["EmergencyResponseResult"] = None


# ---------------------------------------------------------------------------
# Internal intermediate types — one per sub-agent, never exposed in OpenAPI
# ---------------------------------------------------------------------------

class CrimeAnalysis(BaseModel):
    crime_risk: RiskLevel
    score_contribution: int = Field(..., ge=0, le=100)


class LiveCrimeAnalysis(BaseModel):
    """Full output of the Crime Intelligence Agent."""

    crime_risk: RiskLevel
    nearby_crimes: int = Field(default=0, ge=0)
    score_contribution: int = Field(..., ge=0, le=100)
    crime_locations: list[CrimeLocationDetail] = Field(default_factory=list)
    is_live: bool = False


class WeatherAnalysis(BaseModel):
    condition: str
    score_contribution: int = Field(..., ge=0, le=100)
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_pct: Optional[int] = None
    wind_kph: Optional[float] = None
    visibility_km: Optional[float] = None
    is_live: bool = False


class EmergencyServicesAnalysis(BaseModel):
    nearby_police: int = Field(..., ge=0)
    nearby_hospitals: int = Field(..., ge=0)
    score_contribution: int = Field(..., ge=0, le=100)


class InfrastructureAnalysis(BaseModel):
    rating: InfrastructureRating
    score_contribution: int = Field(..., ge=0, le=100)


class LiveInfrastructureAnalysis(BaseModel):
    # Required fields first — Pydantic v2 requires fields without defaults
    # to be declared before fields with defaults.
    rating: InfrastructureRating
    score_contribution: int = Field(..., ge=0, le=100)
    # Defaulted count fields
    nearby_police: int = Field(default=0, ge=0)
    nearby_hospitals: int = Field(default=0, ge=0)
    nearby_fire_stations: int = Field(default=0, ge=0)
    nearby_petrol_pumps: int = Field(default=0, ge=0)
    nearby_pharmacies: int = Field(default=0, ge=0)
    nearby_metro_stations: int = Field(default=0, ge=0)
    is_live: bool = False
    # Facility detail lists
    facility_police: list[FacilityDetail] = Field(default_factory=list)
    facility_hospitals: list[FacilityDetail] = Field(default_factory=list)
    facility_fire_stations: list[FacilityDetail] = Field(default_factory=list)
    facility_petrol_pumps: list[FacilityDetail] = Field(default_factory=list)
    facility_pharmacies: list[FacilityDetail] = Field(default_factory=list)
    facility_metro_stations: list[FacilityDetail] = Field(default_factory=list)


class RouteAnalysis(BaseModel):
    distance_km: float
    duration_min: float
    coordinates: list[list[float]] = Field(
        default_factory=list,
        description="Ordered [lon, lat] pairs along the full route",
    )
    is_live: bool = False


class TrafficAnalysis(BaseModel):
    traffic: str
    traffic_score: int = Field(..., ge=0, le=100)
    traffic_rating: str
    congestion_percentage: int = Field(..., ge=0, le=100)
    average_speed_kph: float
    free_flow_speed_kph: float
    delay_minutes: float
    incidents: int = Field(..., ge=0)
    traffic_live: bool = False


# ---------------------------------------------------------------------------
# Route Optimization schemas
# ---------------------------------------------------------------------------

class RouteOption(BaseModel):
    """One candidate route with full analysis — returned by the Route Optimization Agent."""
    route_index: int
    preference: str = Field(..., description="ORS routing preference: recommended | fastest | shortest")
    safety_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    recommended: bool = False
    distance_km: float
    duration_min: float
    crime_risk: RiskLevel
    weather: str
    infrastructure: InfrastructureRating
    traffic: str
    traffic_score: int
    congestion_percentage: int
    delay_minutes: float
    geometry: Optional[RiskRouteGeometry] = None
    crime_locations: list[CrimeLocationDetail] = Field(default_factory=list)


class RouteOptimizationResponse(BaseModel):
    source: str
    destination: str
    routes: list[RouteOption]
    recommended_index: int = Field(..., description="Index of the safest route in the routes list")
    fastest_index: int = Field(default=0, description="Index of the fastest route (minimum duration) in the routes list")
