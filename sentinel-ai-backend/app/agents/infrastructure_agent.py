"""
InfrastructureAgent — evaluates emergency infrastructure along a route.

Scoring model (capped at 100):
  Police station  : +20 per facility (max 2 counted)
  Hospital        : +20 per facility (max 2 counted)
  Fire station    : +15 per facility (max 2 counted)
  Pharmacy        : +10 per facility (max 3 counted)
  Petrol pump     : +5  per facility (max 3 counted)
  Metro station   : +5  per facility (max 3 counted)

Rating thresholds:
  80–100 → Excellent
  60–79  → Good
  40–59  → Fair
  0–39   → Poor

Fallback (rating="Unknown", score=40) is returned ONLY when Overpass is
genuinely unreachable.  Every fallback path logs the exact reason.
"""

import structlog

from app.schemas.risk import FacilityDetail, LiveInfrastructureAnalysis
from app.services.infrastructure_service import (
    FacilityItem,
    InfrastructureFacilities,
    InfrastructureServiceError,
    get_infrastructure_along_route,
)

logger = structlog.get_logger(__name__)

# (points_per_unit, max_units_counted)
_WEIGHTS: dict[str, tuple[int, int]] = {
    "police":         (20, 2),
    "hospitals":      (20, 2),
    "fire_stations":  (15, 2),
    "pharmacies":     (10, 3),
    "petrol_pumps":   (5,  3),
    "metro_stations": (5,  3),
}

_SCORE_CAP = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calculate_score(f: InfrastructureFacilities) -> int:
    raw = (
        min(f.police,         _WEIGHTS["police"][1])         * _WEIGHTS["police"][0]
        + min(f.hospitals,    _WEIGHTS["hospitals"][1])       * _WEIGHTS["hospitals"][0]
        + min(f.fire_stations,_WEIGHTS["fire_stations"][1])   * _WEIGHTS["fire_stations"][0]
        + min(f.pharmacies,   _WEIGHTS["pharmacies"][1])      * _WEIGHTS["pharmacies"][0]
        + min(f.petrol_pumps, _WEIGHTS["petrol_pumps"][1])    * _WEIGHTS["petrol_pumps"][0]
        + min(f.metro_stations,_WEIGHTS["metro_stations"][1]) * _WEIGHTS["metro_stations"][0]
    )
    return min(raw, _SCORE_CAP)


def _score_to_rating(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Poor"


def _to_detail(items: list[FacilityItem]) -> list[FacilityDetail]:
    return [
        FacilityDetail(
            id=item.id,
            name=item.name,
            type=item.type,
            latitude=item.latitude,
            longitude=item.longitude,
        )
        for item in items
        if not (item.latitude == 0.0 and item.longitude == 0.0)
    ]


def _fallback(reason: str) -> LiveInfrastructureAnalysis:
    """Return a neutral fallback and log exactly why it was triggered."""
    logger.warning(
        "Infrastructure Agent using fallback",
        reason=reason,
        rating="Unknown",
        score_contribution=40,
    )
    return LiveInfrastructureAnalysis(
        rating="Unknown",
        score_contribution=40,
        nearby_police=0,
        nearby_hospitals=0,
        nearby_fire_stations=0,
        nearby_petrol_pumps=0,
        nearby_pharmacies=0,
        nearby_metro_stations=0,
        facility_police=[],
        facility_hospitals=[],
        facility_fire_stations=[],
        facility_petrol_pumps=[],
        facility_pharmacies=[],
        facility_metro_stations=[],
        is_live=False,
    )


# ---------------------------------------------------------------------------
# Public async function
# ---------------------------------------------------------------------------

async def analyze_infrastructure(
    coordinates: list[list[float]],
) -> LiveInfrastructureAnalysis:
    """
    Query Overpass for facilities along the route and return a scored result.
    Never raises — every error path returns _fallback() with a logged reason.
    """
    # ── Guard: no coordinates ────────────────────────────────────────────────
    if not coordinates:
        return _fallback(
            f"No coordinates received from Route Agent (list is empty)"
        )

    logger.info(
        "Infrastructure Agent started",
        coordinate_count=len(coordinates),
        first_coord=coordinates[0],
        last_coord=coordinates[-1],
    )

    # ── Call Overpass ────────────────────────────────────────────────────────
    try:
        facilities: InfrastructureFacilities = await get_infrastructure_along_route(
            coordinates
        )
    except InfrastructureServiceError as exc:
        return _fallback(f"InfrastructureServiceError: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _fallback(f"Unexpected exception from InfrastructureService: {type(exc).__name__}: {exc}")

    # ── Score and rate (0 facilities → "Poor", not "Unknown") ───────────────
    score = _calculate_score(facilities)
    rating = _score_to_rating(score)

    logger.info(
        "Infrastructure Agent complete — live result",
        score=score,
        rating=rating,
        police=facilities.police,
        hospitals=facilities.hospitals,
        fire_stations=facilities.fire_stations,
        petrol_pumps=facilities.petrol_pumps,
        pharmacies=facilities.pharmacies,
        metro_stations=facilities.metro_stations,
    )

    return LiveInfrastructureAnalysis(
        rating=rating,
        score_contribution=score,
        nearby_police=facilities.police,
        nearby_hospitals=facilities.hospitals,
        nearby_fire_stations=facilities.fire_stations,
        nearby_petrol_pumps=facilities.petrol_pumps,
        nearby_pharmacies=facilities.pharmacies,
        nearby_metro_stations=facilities.metro_stations,
        facility_police=_to_detail(facilities.police_list),
        facility_hospitals=_to_detail(facilities.hospitals_list),
        facility_fire_stations=_to_detail(facilities.fire_stations_list),
        facility_petrol_pumps=_to_detail(facilities.petrol_pumps_list),
        facility_pharmacies=_to_detail(facilities.pharmacies_list),
        facility_metro_stations=_to_detail(facilities.metro_stations_list),
        is_live=facilities.is_live,
    )
