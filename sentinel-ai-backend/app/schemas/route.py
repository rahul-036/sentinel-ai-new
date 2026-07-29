from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class Coordinate(BaseModel):
    lon: float = Field(..., description="Longitude (WGS-84)")
    lat: float = Field(..., description="Latitude (WGS-84)")


# ---------------------------------------------------------------------------
# Public request / response
# ---------------------------------------------------------------------------

class RouteAnalysisRequest(BaseModel):
    source: str = Field(..., min_length=1, examples=["Hyderabad"])
    destination: str = Field(..., min_length=1, examples=["Gachibowli"])


class RouteGeometry(BaseModel):
    coordinates: list[Coordinate] = Field(
        ...,
        description="Ordered list of [lon, lat] points along the route",
    )
    bbox: list[float] = Field(
        ...,
        description="Bounding box [min_lon, min_lat, max_lon, max_lat]",
    )
    total_points: int = Field(..., description="Number of coordinate points")


class RouteSegment(BaseModel):
    segment_index: int = Field(..., description="0-based position in the segment list")
    distance_km: float
    duration_min: float
    start: Coordinate
    end: Coordinate
    coordinates: list[Coordinate] = Field(
        ..., description="All points belonging to this segment"
    )
    weather_risk: Optional[str] = None
    crime_risk: Optional[str] = None
    infrastructure_risk: Optional[str] = None
    traffic_risk: Optional[str] = None


class RouteAnalysisResponse(BaseModel):
    source: str
    destination: str
    distance_km: float = Field(..., description="Total route distance in kilometres")
    duration_min: float = Field(..., description="Estimated travel time in minutes")
    geometry: RouteGeometry
    segments: list[RouteSegment]
    is_live: bool = Field(
        ...,
        description="True when data comes from ORS; False when falling back to mock",
    )


class RouteAnalysisError(BaseModel):
    error: str
    detail: str
    source: str
    destination: str
