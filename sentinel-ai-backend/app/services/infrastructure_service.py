"""
InfrastructureService — live facility data from OpenStreetMap Overpass API.

Strategy (single bbox query):
  Instead of firing one Overpass request per sampled coordinate (up to 15
  concurrent requests that trigger rate-limiting / 429s), we compute the
  bounding box of the entire route and issue ONE query that covers the whole
  corridor.  A 0.02-degree padding (~2 km) is added on every side so
  facilities just off the road are included.

Coordinate convention:
  ORS / route geometry  → [lon, lat]
  Overpass bbox syntax  → (south, west, north, east)  i.e. (min_lat, min_lon, max_lat, max_lon)
  Returned FacilityDetail → latitude, longitude  (WGS-84, Leaflet-compatible)
"""

from dataclasses import dataclass, field

import httpx
import structlog

logger = structlog.get_logger(__name__)

_OVERPASS_URL = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
_TIMEOUT_SECONDS = 30.0

# Padding added to the route bounding box on every side (degrees).
# 0.02° ≈ 2.2 km — wide enough to catch facilities set back from the road.
_BBOX_PADDING_DEG = 0.02

# Maps OSM tag value → (tag key, normalised facility type for the response)
_FACILITY_TAGS: dict[str, tuple[str, str]] = {
    "police":          ("amenity", "police"),
    "hospital":        ("amenity", "hospital"),
    "fire_station":    ("amenity", "fire_station"),
    "fuel":            ("amenity", "petrol_pump"),
    "pharmacy":        ("amenity", "pharmacy"),
    "subway_entrance": ("railway", "metro_station"),
}


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------

@dataclass
class FacilityItem:
    id: str
    name: str
    type: str
    latitude: float
    longitude: float


@dataclass
class InfrastructureFacilities:
    police:         int = 0
    hospitals:      int = 0
    fire_stations:  int = 0
    petrol_pumps:   int = 0
    pharmacies:     int = 0
    metro_stations: int = 0
    police_list:         list[FacilityItem] = field(default_factory=list)
    hospitals_list:      list[FacilityItem] = field(default_factory=list)
    fire_stations_list:  list[FacilityItem] = field(default_factory=list)
    petrol_pumps_list:   list[FacilityItem] = field(default_factory=list)
    pharmacies_list:     list[FacilityItem] = field(default_factory=list)
    metro_stations_list: list[FacilityItem] = field(default_factory=list)
    is_live: bool = False


class InfrastructureServiceError(Exception):
    """Raised when Overpass is unavailable or returns unusable data."""


# ---------------------------------------------------------------------------
# Bounding box helpers
# ---------------------------------------------------------------------------

def _route_bbox(
    coordinates: list[list[float]],
    padding: float = _BBOX_PADDING_DEG,
) -> tuple[float, float, float, float]:
    """
    Return (south, west, north, east) bounding box for the route with padding.
    coordinates are [lon, lat] pairs.
    """
    lons = [c[0] for c in coordinates]
    lats = [c[1] for c in coordinates]
    return (
        min(lats) - padding,   # south
        min(lons) - padding,   # west
        max(lats) + padding,   # north
        max(lons) + padding,   # east
    )


def _build_bbox_query(south: float, west: float, north: float, east: float) -> str:
    """
    Build a single Overpass QL query covering the entire route bounding box.
    Uses node + way + relation so OSM compounds are not missed.
    bbox syntax: (south,west,north,east)
    """
    bbox = f"{south},{west},{north},{east}"
    lines = ["[out:json][timeout:25];", "("]
    for osm_value, (osm_key, _) in _FACILITY_TAGS.items():
        lines.append(f'  node["{osm_key}"="{osm_value}"]({bbox});')
        lines.append(f'  way["{osm_key}"="{osm_value}"]({bbox});')
        lines.append(f'  relation["{osm_key}"="{osm_value}"]({bbox});')
    lines.append(");")
    lines.append("out center;")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Coordinate extraction
# ---------------------------------------------------------------------------

def _element_coords(el: dict) -> tuple[float, float] | None:
    el_type = el.get("type")
    if el_type == "node":
        lat, lon = el.get("lat"), el.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    elif el_type in ("way", "relation"):
        center = el.get("center", {})
        lat, lon = center.get("lat"), center.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    return None


# ---------------------------------------------------------------------------
# Deduplication and processing
# ---------------------------------------------------------------------------

def _process_facilities(elements: list[dict]) -> InfrastructureFacilities:
    seen: set[tuple[str, int]] = set()
    lists: dict[str, list[FacilityItem]] = {
        "police": [], "hospital": [], "fire_station": [],
        "petrol_pump": [], "pharmacy": [], "metro_station": [],
    }

    for el in elements:
        uid = (el.get("type", "node"), el.get("id", 0))
        if uid in seen:
            continue
        seen.add(uid)

        tags: dict = el.get("tags", {})
        amenity = tags.get("amenity", "")
        railway = tags.get("railway", "")

        normalised: str | None = None
        if amenity in ("police", "hospital", "fire_station", "fuel", "pharmacy"):
            normalised = _FACILITY_TAGS[amenity][1]
        elif railway == "subway_entrance":
            normalised = "metro_station"

        if normalised is None:
            continue

        coords = _element_coords(el)
        lat = coords[0] if coords else 0.0
        lon = coords[1] if coords else 0.0

        lists[normalised].append(FacilityItem(
            id=f"{uid[0]}:{uid[1]}",
            name=tags.get("name", ""),
            type=normalised,
            latitude=lat,
            longitude=lon,
        ))

    total = sum(len(v) for v in lists.values())
    return InfrastructureFacilities(
        police=len(lists["police"]),
        hospitals=len(lists["hospital"]),
        fire_stations=len(lists["fire_station"]),
        petrol_pumps=len(lists["petrol_pump"]),
        pharmacies=len(lists["pharmacy"]),
        metro_stations=len(lists["metro_station"]),
        police_list=lists["police"],
        hospitals_list=lists["hospital"],
        fire_stations_list=lists["fire_station"],
        petrol_pumps_list=lists["petrol_pump"],
        pharmacies_list=lists["pharmacy"],
        metro_stations_list=lists["metro_station"],
        is_live=total > 0,
    )


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def get_infrastructure_along_route(
    coordinates: list[list[float]],
) -> InfrastructureFacilities:
    """
    Issue ONE Overpass bbox query covering the full route and return
    deduplicated facility counts + detail lists.

    Raises InfrastructureServiceError on unrecoverable failure.
    """
    if not coordinates:
        raise InfrastructureServiceError(
            "Empty coordinate list — cannot query infrastructure."
        )

    south, west, north, east = _route_bbox(coordinates)
    query = _build_bbox_query(south, west, north, east)

    logger.info(
        "Overpass bbox query starting",
        total_coords=len(coordinates),
        bbox_south=round(south, 5),
        bbox_west=round(west, 5),
        bbox_north=round(north, 5),
        bbox_east=round(east, 5),
        overpass_url=_OVERPASS_URL,
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                _OVERPASS_URL,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        logger.info(
            "Overpass HTTP response received",
            status_code=response.status_code,
            response_bytes=len(response.content),
        )

        response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise InfrastructureServiceError(
            f"Overpass request timed out after {_TIMEOUT_SECONDS}s: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise InfrastructureServiceError(
            f"Overpass HTTP {exc.response.status_code}: {exc.response.text[:300]}"
        ) from exc
    except httpx.RequestError as exc:
        raise InfrastructureServiceError(
            f"Overpass network error: {exc}"
        ) from exc

    try:
        elements: list[dict] = response.json().get("elements", [])
    except ValueError as exc:
        raise InfrastructureServiceError(
            f"Overpass returned non-JSON response: {exc}"
        ) from exc

    logger.info(
        "Overpass raw elements received",
        raw_element_count=len(elements),
    )

    facilities = _process_facilities(elements)

    logger.info(
        "Infrastructure query complete",
        is_live=facilities.is_live,
        police=facilities.police,
        hospitals=facilities.hospitals,
        fire_stations=facilities.fire_stations,
        petrol_pumps=facilities.petrol_pumps,
        pharmacies=facilities.pharmacies,
        metro_stations=facilities.metro_stations,
    )

    return facilities
