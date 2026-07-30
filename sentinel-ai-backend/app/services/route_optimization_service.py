"""
RouteOptimizationService — fetches multiple candidate routes from ORS.

Strategy:
  ORS driving-car supports a `preference` parameter:
    - recommended  (default — balanced)
    - fastest      (minimise travel time)
    - shortest     (minimise distance)

  We geocode source + destination once, then fire all three direction
  requests concurrently.  Each result is returned as a RawRoute dataclass
  so the Route Optimization Agent can score them independently.

  If a preference fails (e.g. ORS returns the same geometry as another),
  we still return the others — the agent always gets at least one route.
"""

import asyncio
from dataclasses import dataclass, field

import httpx
import structlog

from app.core.config import get_settings
from app.services.route_service import RouteServiceError, _geocode  # reuse geocoder

logger = structlog.get_logger(__name__)

_ORS_BASE = "https://api.openrouteservice.org"
_TIMEOUT_SECONDS = 15.0
_PREFERENCES = ["recommended", "fastest", "shortest"]


# ---------------------------------------------------------------------------
# Public data structure
# ---------------------------------------------------------------------------

@dataclass
class RawRoute:
    preference: str
    distance_km: float
    duration_min: float
    coordinates: list[list[float]]   # [[lon, lat], ...]


class RouteOptimizationServiceError(Exception):
    """Raised when no routes could be fetched at all."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _fetch_route(
    client: httpx.AsyncClient,
    src: list[float],
    dst: list[float],
    preference: str,
) -> RawRoute | None:
    """Fetch one ORS route for the given preference. Returns None on failure."""
    url = f"{_ORS_BASE}/v2/directions/driving-car/geojson"
    body = {
        "coordinates": [src, dst],
        "preference": preference,
        "instructions": False,
        "geometry": True,
    }
    try:
        r = await client.post(url, json=body)
        r.raise_for_status()
        data = r.json()
        feature = data["features"][0]
        props = feature["properties"]
        summary = props["summary"]
        raw_coords: list[list[float]] = feature["geometry"]["coordinates"]
        return RawRoute(
            preference=preference,
            distance_km=round(summary["distance"] / 1000, 2),
            duration_min=round(summary["duration"] / 60, 2),
            coordinates=raw_coords,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Route optimization: preference fetch failed",
            preference=preference,
            error=str(exc),
        )
        return None


def _deduplicate(routes: list[RawRoute]) -> list[RawRoute]:
    """
    Remove routes whose coordinate list is identical to an earlier one.
    ORS sometimes returns the same geometry for different preferences.
    """
    seen: set[tuple[float, float]] = set()
    unique: list[RawRoute] = []
    for r in routes:
        # Use first + last + midpoint as a cheap fingerprint
        n = len(r.coordinates)
        key = (
            tuple(r.coordinates[0]),
            tuple(r.coordinates[n // 2]),
            tuple(r.coordinates[-1]),
        )
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def get_candidate_routes(
    source: str,
    destination: str,
    preferences: list[str] | None = None,
) -> list[RawRoute]:
    """
    Geocode source + destination, then fetch ORS routes concurrently for the
    given preferences (default: recommended / fastest / shortest).

    Returns a deduplicated list of RawRoute objects (at least 1).
    Raises RouteOptimizationServiceError if every preference fails.
    """
    prefs = preferences if preferences is not None else _PREFERENCES
    settings = get_settings()
    if not settings.OPENROUTESERVICE_API_KEY:
        raise RouteOptimizationServiceError(
            "OPENROUTESERVICE_API_KEY is not configured."
        )

    headers = {
        "Authorization": settings.OPENROUTESERVICE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, application/geo+json",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=headers) as client:
        logger.info(
            "Geocoding for route alternatives",
            source=source, destination=destination, preferences=prefs,
        )
        src_coords = await _geocode(client, source, settings.OPENROUTESERVICE_API_KEY)
        dst_coords = await _geocode(client, destination, settings.OPENROUTESERVICE_API_KEY)
        logger.info(
            "Coordinates resolved",
            source=source, src_coords=src_coords,
            destination=destination, dst_coords=dst_coords,
        )

        results = await asyncio.gather(
            *[_fetch_route(client, src_coords, dst_coords, p) for p in prefs]
        )

    routes = [r for r in results if r is not None]
    if not routes:
        raise RouteOptimizationServiceError(
            "All ORS route preferences failed — cannot fetch alternative routes."
        )

    unique = _deduplicate(routes)
    logger.info(
        "Route alternatives fetched",
        total=len(routes),
        unique=len(unique),
        preferences=prefs,
    )
    return unique
