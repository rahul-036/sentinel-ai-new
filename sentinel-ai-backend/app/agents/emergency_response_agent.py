"""
Emergency Response Agent.

Triggered automatically when:
  - Risk level is High or Critical (called from RiskAssessmentAgent.run())
  - SOS button is pressed (same pipeline, risk level already known)

Reuses:
  - Infrastructure Agent output (facility_police, facility_hospitals,
    facility_fire_stations already fetched by the main pipeline)
  - Traffic Agent output (average_speed_kph for ETA estimation)

Logic:
  1. Pick the nearest police station, hospital, and fire station from the
     facility lists already returned by the Infrastructure Agent.
  2. Estimate ETA to each using straight-line distance + average road speed
     (with a 1.4× detour factor to approximate actual road distance).
  3. Return EmergencyResponseResult — never raises.

Distance formula: Haversine (accurate enough for city-scale distances).
"""

import math

import structlog

from app.schemas.risk import EmergencyFacilityInfo, EmergencyResponseResult, FacilityDetail

logger = structlog.get_logger(__name__)

_DETOUR_FACTOR = 1.4          # road distance ≈ 1.4 × straight-line
_DEFAULT_SPEED_KPH = 30.0     # fallback when TomTom data unavailable
_MIN_SPEED_KPH = 10.0         # floor to avoid division-by-zero / absurd ETAs
_EARTH_RADIUS_KM = 6371.0

EMERGENCY_CONTACTS = {
    "Police":    "112",
    "Ambulance": "108",
    "Fire":      "101",
}


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two WGS-84 points."""
    r = _EARTH_RADIUS_KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _eta_minutes(distance_km: float, speed_kph: float) -> float:
    """Estimate travel time in minutes using road-adjusted distance."""
    road_km = distance_km * _DETOUR_FACTOR
    effective_speed = max(speed_kph, _MIN_SPEED_KPH)
    return round((road_km / effective_speed) * 60, 1)


# ---------------------------------------------------------------------------
# Nearest-facility selector
# ---------------------------------------------------------------------------

def _nearest(
    facilities: list[FacilityDetail],
    route_coords: list[list[float]],
    facility_type: str,
) -> FacilityDetail | None:
    """
    Return the FacilityDetail closest to any point on the route.
    Uses the route midpoint as a representative location for speed.
    """
    if not facilities or not route_coords:
        return None

    # Use route midpoint as reference
    mid = route_coords[len(route_coords) // 2]
    ref_lon, ref_lat = mid[0], mid[1]

    best: FacilityDetail | None = None
    best_dist = float("inf")
    for f in facilities:
        if f.latitude == 0.0 and f.longitude == 0.0:
            continue
        d = _haversine_km(ref_lat, ref_lon, f.latitude, f.longitude)
        if d < best_dist:
            best_dist = d
            best = f

    return best


def _build_facility_info(
    facility: FacilityDetail | None,
    distance_km: float | None,
    eta_min: float | None,
    fallback_name: str,
) -> EmergencyFacilityInfo:
    if facility is None:
        return EmergencyFacilityInfo(
            name=f"No {fallback_name} found nearby",
            distance_km=None,
            eta_minutes=None,
            latitude=None,
            longitude=None,
            available=False,
        )
    return EmergencyFacilityInfo(
        name=facility.name or fallback_name,
        distance_km=round(distance_km, 2) if distance_km is not None else None,
        eta_minutes=eta_min,
        latitude=facility.latitude,
        longitude=facility.longitude,
        available=True,
    )


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def run_emergency_response(
    risk_level: str,
    route_coords: list[list[float]],
    facility_police: list[FacilityDetail],
    facility_hospitals: list[FacilityDetail],
    facility_fire_stations: list[FacilityDetail],
    average_speed_kph: float,
    triggered_by_sos: bool = False,
) -> EmergencyResponseResult:
    """
    Compute nearest emergency facilities and ETAs.
    Never raises — returns a safe fallback on any error.
    """
    triggered = triggered_by_sos or risk_level in ("High", "Critical")
    if not triggered:
        return EmergencyResponseResult(
            activated=False,
            trigger_reason="Risk level is Low or Medium — emergency response not required.",
            nearest_police=EmergencyFacilityInfo(name="N/A", available=False),
            nearest_hospital=EmergencyFacilityInfo(name="N/A", available=False),
            nearest_fire_station=EmergencyFacilityInfo(name="N/A", available=False),
            emergency_contacts=EMERGENCY_CONTACTS,
            status="Standby",
        )

    trigger_reason = (
        "SOS activated by user." if triggered_by_sos
        else f"Risk level is {risk_level} — emergency response activated automatically."
    )

    logger.info(
        "Emergency Response Agent activated",
        risk_level=risk_level,
        triggered_by_sos=triggered_by_sos,
        police_count=len(facility_police),
        hospital_count=len(facility_hospitals),
        fire_count=len(facility_fire_stations),
    )

    speed = average_speed_kph if average_speed_kph >= _MIN_SPEED_KPH else _DEFAULT_SPEED_KPH
    mid = route_coords[len(route_coords) // 2] if route_coords else [0.0, 0.0]
    ref_lon, ref_lat = mid[0], mid[1]

    def _dist_and_eta(f: FacilityDetail | None) -> tuple[float | None, float | None]:
        if f is None or (f.latitude == 0.0 and f.longitude == 0.0):
            return None, None
        d = _haversine_km(ref_lat, ref_lon, f.latitude, f.longitude)
        return d, _eta_minutes(d, speed)

    nearest_police_f    = _nearest(facility_police,        route_coords, "police")
    nearest_hospital_f  = _nearest(facility_hospitals,     route_coords, "hospital")
    nearest_fire_f      = _nearest(facility_fire_stations, route_coords, "fire_station")

    pd, pe = _dist_and_eta(nearest_police_f)
    hd, he = _dist_and_eta(nearest_hospital_f)
    fd, fe = _dist_and_eta(nearest_fire_f)

    logger.info(
        "Emergency Response Agent complete",
        police_eta=pe,
        hospital_eta=he,
        fire_eta=fe,
    )

    return EmergencyResponseResult(
        activated=True,
        trigger_reason=trigger_reason,
        nearest_police=_build_facility_info(nearest_police_f,   pd, pe, "Police Station"),
        nearest_hospital=_build_facility_info(nearest_hospital_f, hd, he, "Hospital"),
        nearest_fire_station=_build_facility_info(nearest_fire_f, fd, fe, "Fire Station"),
        emergency_contacts=EMERGENCY_CONTACTS,
        status="Active — Emergency services identified",
    )
