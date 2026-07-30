import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.agents.route_optimization_agent import optimize_route
from app.schemas.risk import RiskAnalysisRequest, RouteOptimizationResponse
from app.services.route_service import RouteServiceError

router = APIRouter(prefix="/route-optimization", tags=["route-optimization"])
logger = structlog.get_logger(__name__)


@router.post(
    "/analyze",
    response_model=RouteOptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimize route safety",
    description=(
        "Fetches up to 3 candidate routes (recommended / fastest / shortest) from ORS, "
        "scores each using Crime, Weather, Infrastructure, and Traffic agents, "
        "and returns all routes with the safest one marked as recommended."
    ),
    responses={
        422: {"description": "Location not found or invalid input"},
    },
)
async def analyze_route_optimization(
    payload: RiskAnalysisRequest,
) -> RouteOptimizationResponse | JSONResponse:
    try:
        return await optimize_route(
            source=payload.source,
            destination=payload.destination,
        )
    except RouteServiceError as exc:
        logger.warning(
            "Route optimization: geocoding/routing failed",
            source=payload.source,
            destination=payload.destination,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": str(exc), "detail": exc.detail},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Route optimization: unexpected error",
            source=payload.source,
            destination=payload.destination,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Route optimization failed",
                "detail": (
                    f"Could not find a route from '{payload.source}' to '{payload.destination}'. "
                    "Please check the place names and try again."
                ),
            },
        )
