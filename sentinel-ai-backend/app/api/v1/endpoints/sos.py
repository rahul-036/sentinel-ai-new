from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.agents.sos_agent import SOSAgent
from app.schemas.sos import (
    NotifiedGuardian,
    SOSHistoryItem,
    SOSRequest,
    SOSResponseV2,
)
from app.services.sos_service import get_all_alerts

router = APIRouter(prefix="/sos", tags=["sos"])


@router.post(
    "/send",
    response_model=SOSResponseV2,
    status_code=status.HTTP_201_CREATED,
    summary="Send an emergency SOS alert",
    description=(
        "Validates the request, generates a unique alert ID, notifies all "
        "registered guardians (simulated in v1), stores the alert, and returns "
        "a full confirmation including guardian notification results."
    ),
)
async def send_sos(payload: SOSRequest) -> SOSResponseV2 | JSONResponse:
    agent = SOSAgent()
    try:
        return await agent.run(payload)
    except RuntimeError as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )


@router.get(
    "/history",
    response_model=list[SOSHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="SOS alert history",
    description="Returns all past SOS alerts, newest first.",
)
async def sos_history() -> list[SOSHistoryItem]:
    alerts = get_all_alerts()
    return [
        SOSHistoryItem(
            alert_id=a.alert_id,
            timestamp=a.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            user_name=a.user_name,
            latitude=a.latitude,
            longitude=a.longitude,
            risk_level=a.risk_level,
            safety_score=a.safety_score,
            guardian_count=len(a.guardians_notified),
            guardians_notified=[
                NotifiedGuardian(
                    id=g["id"],
                    name=g["name"],
                    phone=g["phone"],
                    relation=g["relation"],
                    notification_status=g["notification_status"],
                )
                for g in a.guardians_notified
            ],
            status="dispatched",
        )
        for a in alerts
    ]
