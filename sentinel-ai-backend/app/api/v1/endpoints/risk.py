from fastapi import APIRouter, status

from app.agents.risk_assessment_agent import RiskAssessmentAgent
from app.schemas.risk import RiskAnalysisRequest, RiskAnalysisResponse

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
    agent = RiskAssessmentAgent(source=payload.source, destination=payload.destination)
    return await agent.run()
