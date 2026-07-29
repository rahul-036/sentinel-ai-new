from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Literal type aliases
# ---------------------------------------------------------------------------

RiskLevel = Literal["Low", "Medium", "High", "Critical"]
InfrastructureRating = Literal["Poor", "Fair", "Good", "Excellent", "Unknown"]


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


# ---------------------------------------------------------------------------
# Internal intermediate types — one per sub-agent, never exposed in OpenAPI
# ---------------------------------------------------------------------------

class CrimeAnalysis(BaseModel):
    crime_risk: RiskLevel
    score_contribution: int = Field(..., ge=0, le=100)


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
