import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.route import RouteAnalysisError, RouteAnalysisRequest, RouteAnalysisResponse
from app.services.route_service import RouteServiceError, get_route

router = APIRouter(prefix="/route", tags=["route"])
logger = structlog.get_logger(__name__)


@router.post(
    "/analyze",
    response_model=RouteAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a driving route",
    description=(
        "Geocodes source and destination, fetches driving directions from "
        "OpenRouteService, and returns distance, duration, decoded geometry, "
        "and per-segment data ready for downstream agent analysis."
    ),
    responses={
        503: {
            "model": RouteAnalysisError,
            "description": "ORS unavailable or API key not configured",
        }
    },
)
async def analyze_route(payload: RouteAnalysisRequest) -> RouteAnalysisResponse | JSONResponse:
    try:
        return await get_route(
            source=payload.source,
            destination=payload.destination,
        )
    except RouteServiceError as exc:
        logger.warning(
            "Route analysis failed",
            source=payload.source,
            destination=payload.destination,
            error=str(exc),
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=RouteAnalysisError(
                error=str(exc),
                detail=exc.detail,
                source=payload.source,
                destination=payload.destination,
            ).model_dump(),
        )
