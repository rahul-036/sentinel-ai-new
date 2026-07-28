from typing import Literal

from pydantic import BaseModel, Field


class RiskAnalysisRequest(BaseModel):
    source: str = Field(..., min_length=1, examples=["Hyderabad"])
    destination: str = Field(..., min_length=1, examples=["Gachibowli"])


RiskLevel = Literal["Low", "Medium", "High", "Critical"]
InfrastructureRating = Literal["Poor", "Fair", "Good", "Excellent"]


class RiskAnalysisResponse(BaseModel):
    safety_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    crime_risk: RiskLevel
    weather: str
    # Live weather detail — present when WeatherAPI is reachable
    temperature_c: float | None = None
    feels_like_c: float | None = None
    humidity_pct: int | None = None
    wind_kph: float | None = None
    visibility_km: float | None = None
    weather_live: bool = False
    nearby_police: int = Field(..., ge=0)
    nearby_hospitals: int = Field(..., ge=0)
    infrastructure: InfrastructureRating
    recommendation: str
    reason: str


# ---------------------------------------------------------------------------
# Internal intermediate types — one per sub-agent method.
# Typed explicitly so each method can be replaced independently.
# ---------------------------------------------------------------------------

class CrimeAnalysis(BaseModel):
    crime_risk: RiskLevel
    score_contribution: int = Field(..., ge=0, le=100)


class WeatherAnalysis(BaseModel):
    condition: str
    score_contribution: int = Field(..., ge=0, le=100)
    # Live fields — populated by WeatherService, None when falling back to mock
    temperature_c: float | None = None
    feels_like_c: float | None = None
    humidity_pct: int | None = None
    wind_kph: float | None = None
    visibility_km: float | None = None
    is_live: bool = False


class EmergencyServicesAnalysis(BaseModel):
    nearby_police: int = Field(..., ge=0)
    nearby_hospitals: int = Field(..., ge=0)
    score_contribution: int = Field(..., ge=0, le=100)


class InfrastructureAnalysis(BaseModel):
    rating: InfrastructureRating
    score_contribution: int = Field(..., ge=0, le=100)
