from fastapi import APIRouter, HTTPException, status

from app.agents.risk_assessment_agent import RiskAssessmentAgent
from app.schemas.risk import RiskAnalysisRequest, RiskAnalysisResponse
from app.services.route_service import RouteServiceError

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post(
    "/analyze",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze route risk",
    description=(
        "Runs the Risk Assessment Agent across crime, weather, emergency services, "
        "and infrastructure dimensions and returns a consolidated safety score."
    ),
)
async def analyze_risk(payload: RiskAnalysisRequest) -> RiskAnalysisResponse:
    try:
        agent = RiskAssessmentAgent(source=payload.source, destination=payload.destination)
        return await agent.run()
    except RouteServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail or str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Risk analysis service temporarily unavailable: {exc}",
        ) from exc
