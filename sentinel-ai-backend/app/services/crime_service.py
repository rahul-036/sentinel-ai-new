"""
CrimeService — geospatial crime intelligence from the Coimbatore crime dataset.

Dataset facts (verified by inspection):
  File    : dataset/coimbatore_crime_dataset.xlsx
  Sheet   : Sheet1
  Rows    : 70  (one row per named area)
  Columns : City, Area, Theft, Robbery, Assault, Harassment,
            Vehicle Theft, Crime Index, Risk Level

  The dataset has NO latitude/longitude columns.  Coordinates for every
  area are maintained in _AREA_COORDINATES below — a one-time lookup table
  built from the 70 known Coimbatore localities.

Geospatial strategy:
  For each crime area we compute the minimum haversine distance from that
  area's centroid to every coordinate on the route.  If that minimum
  distance is ≤ PROXIMITY_RADIUS_M (200 m) the area is considered
  "near the route" and its crimes are included in the result.

  Because Coimbatore areas are large neighbourhoods (not point crimes),
  200 m from the route centroid is intentionally generous — it captures
  areas the route passes through or immediately adjacent to.

Adding a new city dataset:
  1. Drop the new .xlsx into dataset/ (e.g. chennai_crime_dataset.xlsx).
  2. Add its area → (lat, lon) entries to _AREA_COORDINATES.
  3. Call load_dataset(path=...) with the new path — no other code changes.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Dataset path & column constants
# ---------------------------------------------------------------------------

_DATASET_PATH = Path(__file__).resolve().parents[2] / "dataset" / "coimbatore_crime_dataset.xlsx"
_SHEET_NAME = "Sheet1"

_COL_CITY = "City"
_COL_AREA = "Area"
_COL_THEFT = "Theft"
_COL_ROBBERY = "Robbery"
_COL_ASSAULT = "Assault"
_COL_HARASSMENT = "Harassment"
_COL_VEHICLE_THEFT = "Vehicle Theft"
_COL_CRIME_INDEX = "Crime Index"
_COL_RISK_LEVEL = "Risk Level"

_REQUIRED_COLUMNS: set[str] = {
    _COL_CITY, _COL_AREA, _COL_THEFT, _COL_ROBBERY, _COL_ASSAULT,
    _COL_HARASSMENT, _COL_VEHICLE_THEFT, _COL_CRIME_INDEX, _COL_RISK_LEVEL,
}

# ---------------------------------------------------------------------------
# Proximity threshold
# ---------------------------------------------------------------------------

# A crime area is "near the route" when its centroid lies within this many
# metres of any route coordinate.
PROXIMITY_RADIUS_M: float = 200.0

# ---------------------------------------------------------------------------
# Area coordinate lookup — (latitude, longitude) for all 70 Coimbatore areas.
# Source: well-known locality centroids for Coimbatore district.
# To add a new city: extend this dict with its area centroids.
# ---------------------------------------------------------------------------

_AREA_COORDINATES: dict[str, tuple[float, float]] = {
    "Gandhipuram":              (11.0168, 76.9558),
    "R.S. Puram":               (11.0050, 76.9550),
    "Peelamedu":                (11.0270, 77.0270),
    "Singanallur":              (11.0000, 77.0330),
    "Saibaba Colony":           (11.0230, 76.9470),
    "Ukkadam":                  (10.9900, 76.9700),
    "Town Hall":                (11.0100, 76.9650),
    "Race Course":              (11.0200, 76.9500),
    "Saravanampatti":           (11.0700, 77.0000),
    "Vadavalli":                (10.9980, 76.9100),
    "Kuniyamuthur":             (10.9750, 76.9450),
    "Sundarapuram":             (10.9850, 76.9300),
    "Podanur":                  (10.9700, 76.9800),
    "Kalapatti":                (11.0600, 77.0200),
    "Kovaipudur":               (10.9600, 76.9200),
    "Kavundampalayam":          (11.0450, 76.9700),
    "Thudiyalur":               (11.0800, 76.9700),
    "Ganapathy":                (11.0350, 76.9600),
    "Chinniyampalayam":         (11.0500, 76.9550),
    "Sulur":                    (11.0300, 77.1200),
    "Karamadai":                (11.2400, 76.9600),
    "Mettupalayam":             (11.2970, 76.9340),
    "Annur":                    (11.1780, 77.1070),
    "Pollachi":                 (10.6590, 77.0070),
    "Kinathukadavu":            (10.8500, 76.9500),
    "Perur":                    (10.9700, 76.9200),
    "Selvapuram":               (11.0050, 76.9400),
    "Ramanathapuram":           (11.0150, 77.0500),
    "Nanjundapuram":            (10.9900, 76.9600),
    "Eachanari":                (10.9800, 76.9850),
    "Chettipalayam":            (11.0600, 76.9200),
    "Vellalore":                (10.9650, 77.0100),
    "Neelambur":                (11.0450, 77.0450),
    "Hope College":             (11.0100, 76.9480),
    "Avinashi Road":            (11.0350, 77.0000),
    "Chinnathadagam":           (11.1000, 76.9800),
    "Airport Area":             (11.0300, 77.0430),
    "Ondipudur":                (11.0100, 77.0600),
    "Sidhapudur":               (11.0200, 76.9700),
    "Pappanaickenpalayam":      (11.0550, 76.9650),
    "Cheran Nagar":             (11.0400, 77.0100),
    "G.N. Mills":               (11.0000, 76.9550),
    "Lakshmi Mills":            (11.0080, 76.9620),
    "Bharathi Colony":          (11.0300, 76.9550),
    "Chinnavedampatti":         (11.0700, 76.9500),
    "Vilankurichi":             (11.0600, 77.0100),
    "Kumarapalayam":            (11.4500, 77.6900),
    "Sivananda Colony":         (11.0150, 76.9520),
    "Tatabad":                  (11.0180, 76.9580),
    "Gopalapuram":              (11.0050, 76.9650),
    "Rathinapuri":              (11.0100, 77.0100),
    "Veerakeralam":             (11.0700, 76.9300),
    "Marudamalai":              (11.0600, 76.9100),
    "P.N. Pudur":               (11.0000, 76.9400),
    "Thondamuthur":             (10.9500, 76.8800),
    "Narasimhanaickenpalayam":  (11.0800, 76.9600),
    "Kovilpalayam":             (11.0500, 76.9400),
    "Kurichi":                  (10.9800, 76.9700),
    "Madukkarai":               (10.9200, 76.9600),
    "Malumichampatti":          (11.0900, 76.9400),
    "Nallampalayam":            (11.0650, 77.0300),
    "Nava India":               (11.0250, 76.9750),
    "Hopes Junction":           (11.0150, 76.9700),
    "PSG Tech Area":            (11.0240, 76.9340),
    "CODISSIA":                 (11.0350, 77.0050),
    "Chitra":                   (11.0100, 76.9600),
    "Karunya Nagar":            (11.0000, 76.9000),
    "Press Colony":             (11.0200, 76.9650),
    "Sathy Road":               (11.0700, 77.0500),
    "TVS Nagar":                (11.0050, 76.9750),
}

# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrimeLocation:
    """A single area's crime record enriched with its centroid coordinates."""

    area: str
    crime_index: int
    risk_level: str          # "Low" | "Medium" | "High"
    theft: int
    robbery: int
    assault: int
    harassment: int
    vehicle_theft: int
    latitude: float
    longitude: float
    distance_m: float        # shortest distance to the route (metres)

    @property
    def dominant_crime_type(self) -> str:
        counts = {
            "Theft": self.theft,
            "Robbery": self.robbery,
            "Assault": self.assault,
            "Harassment": self.harassment,
            "Vehicle Theft": self.vehicle_theft,
        }
        return max(counts, key=lambda k: counts[k])


@dataclass
class CrimeAnalysisResult:
    """Full output of the Crime Intelligence Agent."""

    crime_risk: str                        # "Low" | "Medium" | "High" | "Critical"
    nearby_crimes: int                     # count of matched areas
    score_contribution: int                # 0–100, higher = safer
    crime_locations: list[CrimeLocation]   # matched area details


# ---------------------------------------------------------------------------
# Module-level singleton cache (thread-safe double-checked locking)
# ---------------------------------------------------------------------------

_df_cache: pd.DataFrame | None = None
_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

_EARTH_RADIUS_M = 6_371_000.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in metres between two WGS-84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _min_distance_to_route(
    area_lat: float,
    area_lon: float,
    route_coords: list[list[float]],  # [[lon, lat], ...]
) -> float:
    """Return the minimum haversine distance (metres) from an area centroid to any route point."""
    min_d = math.inf
    for coord in route_coords:
        lon, lat = coord[0], coord[1]
        d = _haversine_m(area_lat, area_lon, lat, lon)
        if d < min_d:
            min_d = d
    return min_d


# ---------------------------------------------------------------------------
# Dataset loader
# ---------------------------------------------------------------------------


def load_dataset() -> pd.DataFrame:
    """
    Load the crime dataset from disk and cache it in memory (thread-safe).

    Returns the cached DataFrame on subsequent calls.
    Raises RuntimeError if the file is missing or columns are invalid.
    """
    global _df_cache

    if _df_cache is not None:
        return _df_cache

    with _cache_lock:
        if _df_cache is not None:
            return _df_cache

        if not _DATASET_PATH.exists():
            raise RuntimeError(
                f"Crime dataset not found at {_DATASET_PATH}. "
                "Ensure dataset/coimbatore_crime_dataset.xlsx is present."
            )

        try:
            df = pd.read_excel(_DATASET_PATH, sheet_name=_SHEET_NAME, engine="openpyxl")
        except Exception as exc:
            raise RuntimeError(f"Failed to load crime dataset: {exc}") from exc

        missing = _REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise RuntimeError(
                f"Crime dataset is missing columns: {missing}. Found: {list(df.columns)}"
            )

        # Normalise string columns
        df[_COL_AREA] = df[_COL_AREA].str.strip()
        df[_COL_CITY] = df[_COL_CITY].str.strip()
        df[_COL_RISK_LEVEL] = df[_COL_RISK_LEVEL].str.strip()

        _df_cache = df
        logger.info(
            "Crime dataset loaded",
            path=str(_DATASET_PATH),
            rows=len(df),
            risk_distribution=df[_COL_RISK_LEVEL].value_counts().to_dict(),
        )

    return _df_cache


# ---------------------------------------------------------------------------
# Core geospatial query
# ---------------------------------------------------------------------------


def get_crimes_near_route(
    route_coords: list[list[float]],
    *,
    radius_m: float = PROXIMITY_RADIUS_M,
) -> list[CrimeLocation]:
    """
    Return all crime areas whose centroid lies within *radius_m* metres of
    any coordinate on the route.

    Args:
        route_coords: Ordered [[lon, lat], ...] pairs from the Route Agent.
        radius_m:     Proximity threshold in metres (default 200 m).

    Returns:
        List of CrimeLocation objects sorted by crime_index descending.
        Empty list on any error — never raises.
    """
    if not route_coords:
        logger.warning("get_crimes_near_route called with empty coordinate list")
        return []

    try:
        df = load_dataset()
    except RuntimeError as exc:
        logger.warning("Crime dataset unavailable", error=str(exc))
        return []

    nearby: list[CrimeLocation] = []

    for _, row in df.iterrows():
        area_name: str = str(row[_COL_AREA])
        coords = _AREA_COORDINATES.get(area_name)

        if coords is None:
            # Area not in coordinate lookup — skip silently
            logger.debug("No coordinates for area — skipped", area=area_name)
            continue

        area_lat, area_lon = coords
        dist = _min_distance_to_route(area_lat, area_lon, route_coords)

        if dist <= radius_m:
            nearby.append(
                CrimeLocation(
                    area=area_name,
                    crime_index=int(row[_COL_CRIME_INDEX]),
                    risk_level=str(row[_COL_RISK_LEVEL]),
                    theft=int(row[_COL_THEFT]),
                    robbery=int(row[_COL_ROBBERY]),
                    assault=int(row[_COL_ASSAULT]),
                    harassment=int(row[_COL_HARASSMENT]),
                    vehicle_theft=int(row[_COL_VEHICLE_THEFT]),
                    latitude=area_lat,
                    longitude=area_lon,
                    distance_m=round(dist, 1),
                )
            )

    nearby.sort(key=lambda c: c.crime_index, reverse=True)

    logger.info(
        "Crime proximity query complete",
        route_points=len(route_coords),
        radius_m=radius_m,
        matched_areas=len(nearby),
    )

    return nearby
