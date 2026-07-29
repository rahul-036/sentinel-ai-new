"""
RouteService — live route data from OpenRouteService (ORS).

Responsibilities:
  1. Geocode source and destination strings to [lon, lat] via ORS Geocoding.
  2. Fetch driving directions from ORS Directions API (GeoJSON profile).
  3. Decode the GeoJSON LineString geometry into typed Coordinate objects.
  4. Split the full route into RouteSegments using the ORS step data so that
     future sub-agents (Weather, Crime, Infrastructure, Traffic) can analyse
     each segment independently.
  5. On any failure log a warning and raise RouteServiceError so the endpoint
     can return a structured 503 — never a raw 500.

ORS endpoints used:
  Geocoding  : GET  https://api.openrouteservice.org/geocode/search
  Directions : POST https://api.openrouteservice.org/v2/directions/driving-car/geojson
"""

import httpx
import structlog

from app.core.config import get_settings
from app.schemas.route import (
    Coordinate,
    RouteAnalysisResponse,
    RouteGeometry,
    RouteSegment,
)
# RouteSegment is defined before RouteAnalysisResponse in route.py — no model_rebuild needed

logger = structlog.get_logger(__name__)

_ORS_BASE = "https://api.openrouteservice.org"
_TIMEOUT_SECONDS = 12.0

# Number of equal-length segments to split the route into.
# Each segment becomes the unit of analysis for future sub-agents.
_SEGMENT_COUNT = 5


# ---------------------------------------------------------------------------
# Internal exception
# ---------------------------------------------------------------------------

class RouteServiceError(Exception):
    """Raised when ORS is unavailable or returns unusable data."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail or message


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

async def _geocode(client: httpx.AsyncClient, location: str, api_key: str) -> list[float]:
    """Return [lon, lat] for a free-text location string via ORS Geocoding.

    Raises RouteServiceError on any failure.
    """
    url = f"{_ORS_BASE}/geocode/search"
    params = {
        "api_key": api_key,
        "text": location,
        "size": 1,
    }

    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])
        if not features:
            raise RouteServiceError(
                f"Location not found: '{location}'",
                detail=f"ORS geocoding returned no results for '{location}'. "
                       "Try a more specific place name.",
            )
        coords: list[float] = features[0]["geometry"]["coordinates"]  # [lon, lat]
        logger.debug("Geocoded location", location=location, coords=coords)
        return coords

    except httpx.TimeoutException as exc:
        raise RouteServiceError(
            f"Geocoding timed out for '{location}'",
            detail="ORS geocoding request exceeded the timeout limit.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RouteServiceError(
            f"ORS geocoding error for '{location}'",
            detail=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
        ) from exc
    except (httpx.RequestError, KeyError, IndexError, ValueError) as exc:
        raise RouteServiceError(
            f"Geocoding failed for '{location}'",
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _build_geometry(raw_coords: list[list[float]]) -> RouteGeometry:
    """Convert a raw GeoJSON coordinate list into a typed RouteGeometry."""
    coordinates = [Coordinate(lon=c[0], lat=c[1]) for c in raw_coords]

    lons = [c.lon for c in coordinates]
    lats = [c.lat for c in coordinates]
    bbox = [min(lons), min(lats), max(lons), max(lats)]

    return RouteGeometry(
        coordinates=coordinates,
        bbox=bbox,
        total_points=len(coordinates),
    )


def _build_segments(
    raw_coords: list[list[float]],
    ors_segments: list[dict],
) -> list[RouteSegment]:
    """
    Build RouteSegments from ORS step data.

    ORS returns a 'segments' array where each segment contains 'steps'.
    We flatten all steps into a single ordered list and map each step's
    way_points indices back to the decoded coordinate array.

    If ORS provides no usable step data we fall back to splitting the
    coordinate list into _SEGMENT_COUNT equal slices.
    """
    all_coords = [Coordinate(lon=c[0], lat=c[1]) for c in raw_coords]
    segments: list[RouteSegment] = []

    # Flatten ORS steps across all segments
    flat_steps: list[dict] = []
    for seg in ors_segments:
        flat_steps.extend(seg.get("steps", []))

    if flat_steps:
        for idx, step in enumerate(flat_steps):
            wp: list[int] = step.get("way_points", [])
            if len(wp) < 2:
                continue
            start_i, end_i = wp[0], wp[1]
            # Guard against out-of-range indices
            end_i = min(end_i, len(all_coords) - 1)
            step_coords = all_coords[start_i : end_i + 1]
            if not step_coords:
                continue
            segments.append(
                RouteSegment(
                    segment_index=idx,
                    distance_km=round(step.get("distance", 0) / 1000, 3),
                    duration_min=round(step.get("duration", 0) / 60, 2),
                    start=step_coords[0],
                    end=step_coords[-1],
                    coordinates=step_coords,
                )
            )
    else:
        # Fallback: equal-length slices
        n = len(all_coords)
        slice_size = max(2, n // _SEGMENT_COUNT)
        for idx in range(_SEGMENT_COUNT):
            start_i = idx * slice_size
            end_i = start_i + slice_size if idx < _SEGMENT_COUNT - 1 else n
            chunk = all_coords[start_i:end_i]
            if not chunk:
                continue
            segments.append(
                RouteSegment(
                    segment_index=idx,
                    distance_km=0.0,   # unknown without step data
                    duration_min=0.0,
                    start=chunk[0],
                    end=chunk[-1],
                    coordinates=chunk,
                )
            )

    return segments


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def get_route(source: str, destination: str) -> RouteAnalysisResponse:
    """
    Geocode source + destination, fetch ORS driving directions, and return
    a fully-populated RouteAnalysisResponse.

    Raises RouteServiceError on any unrecoverable failure so the endpoint
    can return a clean 503 instead of a raw 500.
    """
    settings = get_settings()

    if not settings.OPENROUTESERVICE_API_KEY:
        raise RouteServiceError(
            "OPENROUTESERVICE_API_KEY is not configured",
            detail="Add OPENROUTESERVICE_API_KEY to your .env file. "
                   "Get a free key at https://openrouteservice.org/",
        )

    headers = {
        "Authorization": settings.OPENROUTESERVICE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, application/geo+json",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=headers) as client:
        # 1. Geocode both ends of the route
        logger.info("Geocoding route endpoints", source=source, destination=destination)
        src_coords = await _geocode(client, source, settings.OPENROUTESERVICE_API_KEY)
        dst_coords = await _geocode(client, destination, settings.OPENROUTESERVICE_API_KEY)

        # 2. Fetch directions
        directions_url = f"{_ORS_BASE}/v2/directions/driving-car/geojson"
        body = {
            "coordinates": [src_coords, dst_coords],
            "instructions": True,
            "geometry": True,
        }

        try:
            response = await client.post(directions_url, json=body)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RouteServiceError(
                "ORS directions request timed out",
                detail="The route calculation exceeded the timeout limit.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RouteServiceError(
                "ORS directions API error",
                detail=f"HTTP {exc.response.status_code}: {exc.response.text[:300]}",
            ) from exc
        except httpx.RequestError as exc:
            raise RouteServiceError(
                "ORS directions request failed",
                detail=str(exc),
            ) from exc

    # 3. Parse response
    try:
        data = response.json()
        feature = data["features"][0]
        props = feature["properties"]
        summary = props["summary"]
        raw_coords: list[list[float]] = feature["geometry"]["coordinates"]
        ors_segments: list[dict] = props.get("segments", [])
    except (KeyError, IndexError, ValueError) as exc:
        raise RouteServiceError(
            "Unexpected ORS response structure",
            detail=str(exc),
        ) from exc

    distance_km = round(summary["distance"] / 1000, 2)
    duration_min = round(summary["duration"] / 60, 2)

    geometry = _build_geometry(raw_coords)
    segments = _build_segments(raw_coords, ors_segments)

    logger.info(
        "Route fetched",
        source=source,
        destination=destination,
        distance_km=distance_km,
        duration_min=duration_min,
        total_points=geometry.total_points,
        segments=len(segments),
    )

    return RouteAnalysisResponse(
        source=source,
        destination=destination,
        distance_km=distance_km,
        duration_min=duration_min,
        geometry=geometry,
        segments=segments,
        is_live=True,
    )
