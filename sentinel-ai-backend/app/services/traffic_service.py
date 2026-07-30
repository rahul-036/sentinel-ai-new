"""
TrafficService — live traffic data from TomTom Traffic API.

Strategy:
  1. Sample up to _MAX_SAMPLE_POINTS evenly-spaced coordinates from the route.
  2. For each sampled point call TomTom Flow Segment Data API to get
     current speed, free-flow speed, and travel time.
  3. Call TomTom Incidents API once using the route bounding box.
  4. Aggregate all flow results and return a single TrafficData dataclass.

TomTom endpoints used:
  Flow      : GET https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json
  Incidents : GET https://api.tomtom.com/traffic/services/5/incidentDetails

Coordinate convention (matches ORS / route geometry):
  coordinates → [lon, lat]
  TomTom point param → "{lat},{lon}"
  TomTom bbox param  → "{min_lon},{min_lat},{max_lon},{max_lat}"
"""

import asyncio
from dataclasses import dataclass, field

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_TOMTOM_BASE = "https://api.tomtom.com"
_TIMEOUT_SECONDS = 10.0
_MAX_SAMPLE_POINTS = 5
_BBOX_PADDING_DEG = 0.02


# ---------------------------------------------------------------------------
# Public data structure
# ---------------------------------------------------------------------------

@dataclass
class TrafficData:
    congestion_percentage: int = 0
    average_speed_kph: float = 0.0
    free_flow_speed_kph: float = 0.0
    delay_minutes: float = 0.0
    incidents: int = 0
    confidence: float = 1.0
    is_live: bool = False


class TrafficServiceError(Exception):
    """Raised when TomTom is unavailable or the API key is missing."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sample_coordinates(
    coordinates: list[list[float]], n: int = _MAX_SAMPLE_POINTS
) -> list[list[float]]:
    """Return n evenly-spaced [lon, lat] points from the full coordinate list."""
    if len(coordinates) <= n:
        return coordinates
    step = (len(coordinates) - 1) / (n - 1)
    return [coordinates[round(i * step)] for i in range(n)]


def _route_bbox(
    coordinates: list[list[float]],
) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) with padding."""
    lons = [c[0] for c in coordinates]
    lats = [c[1] for c in coordinates]
    p = _BBOX_PADDING_DEG
    return (min(lons) - p, min(lats) - p, max(lons) + p, max(lats) + p)


async def _fetch_flow_segment(
    client: httpx.AsyncClient,
    lon: float,
    lat: float,
    api_key: str,
) -> dict:
    """Fetch TomTom Flow Segment Data for a single [lon, lat] point.

    Returns the flowSegmentData dict, or {} on any failure.
    """
    url = f"{_TOMTOM_BASE}/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {"key": api_key, "point": f"{lat},{lon}", "unit": "KMPH"}
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json().get("flowSegmentData", {})
    except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
        logger.warning(
            "Flow segment fetch failed",
            lat=lat,
            lon=lon,
            error=str(exc),
        )
        return {}


async def _fetch_incidents(
    client: httpx.AsyncClient,
    bbox: tuple[float, float, float, float],
    api_key: str,
) -> int:
    """Return the number of traffic incidents within the route bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    url = f"{_TOMTOM_BASE}/traffic/services/5/incidentDetails"
    params = {
        "key": api_key,
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "fields": "{incidents{type}}",
        "language": "en-GB",
        "categoryFilter": "0,1,2,3,4,5,6,7,8,9,10,11",
        "timeValidityFilter": "present",
    }
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return len(r.json().get("incidents", []))
    except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
        logger.warning("Incidents fetch failed", error=str(exc))
        return 0


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def get_traffic_along_route(
    coordinates: list[list[float]],
) -> TrafficData:
    """
    Fetch live TomTom traffic flow and incidents for the route.

    Raises TrafficServiceError on unrecoverable failure so the agent
    can return a clean fallback instead of a raw 500.
    """
    if not coordinates:
        raise TrafficServiceError(
            "Empty coordinate list — cannot query traffic."
        )

    settings = get_settings()
    if not settings.TOMTOM_API_KEY:
        raise TrafficServiceError(
            "TOMTOM_API_KEY is not configured. Add it to your .env file."
        )

    api_key = settings.TOMTOM_API_KEY
    sampled = _sample_coordinates(coordinates)
    bbox = _route_bbox(coordinates)

    logger.info(
        "Traffic service started",
        total_coords=len(coordinates),
        sample_points=len(sampled),
    )

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        flow_tasks = [
            _fetch_flow_segment(client, c[0], c[1], api_key) for c in sampled
        ]
        flow_results, incident_count = await asyncio.gather(
            asyncio.gather(*flow_tasks),
            _fetch_incidents(client, bbox, api_key),
        )

    # Filter out empty responses
    valid = [f for f in flow_results if f.get("currentSpeed")]
    if not valid:
        raise TrafficServiceError(
            "TomTom returned no usable flow data for this route."
        )

    avg_current_speed = sum(f["currentSpeed"] for f in valid) / len(valid)
    avg_free_flow = sum(f.get("freeFlowSpeed", avg_current_speed) for f in valid) / len(valid)
    avg_confidence = sum(f.get("confidence", 1.0) for f in valid) / len(valid)

    # Congestion: how much slower than free-flow, expressed as 0–100 %
    congestion_pct = 0
    if avg_free_flow > 0:
        congestion_pct = max(
            0, min(100, round((1 - avg_current_speed / avg_free_flow) * 100))
        )

    # Delay: average extra travel time per segment vs free-flow (minutes)
    total_delay_s = 0.0
    for f in valid:
        current_tt = f.get("currentTravelTime", 0)
        free_tt = f.get("freeFlowTravelTime", current_tt)
        total_delay_s += max(0.0, current_tt - free_tt)
    delay_min = round((total_delay_s / len(valid)) / 60, 1)

    logger.info(
        "Traffic service complete",
        avg_speed_kph=round(avg_current_speed, 1),
        free_flow_kph=round(avg_free_flow, 1),
        congestion_pct=congestion_pct,
        delay_min=delay_min,
        incidents=incident_count,
        confidence=round(avg_confidence, 2),
        valid_samples=len(valid),
    )

    return TrafficData(
        congestion_percentage=congestion_pct,
        average_speed_kph=round(avg_current_speed, 1),
        free_flow_speed_kph=round(avg_free_flow, 1),
        delay_minutes=delay_min,
        incidents=incident_count,
        confidence=round(avg_confidence, 2),
        is_live=True,
    )
