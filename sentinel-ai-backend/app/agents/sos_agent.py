"""
SOSAgent — orchestrates the full SOS pipeline including guardian notifications.

This agent supersedes GuardianSOSAgent for the /sos/send endpoint.
GuardianSOSAgent is preserved for backward compatibility.

Pipeline:
  1. Validate request (done by FastAPI/Pydantic before agent is called).
  2. Call SOSService.create_sos_alert_v2() which:
       a. Generates alert ID + timestamp.
       b. Notifies all registered guardians via NotificationDispatcher.
       c. Stores the complete alert record.
  3. Map the internal SOSAlert to SOSResponseV2.
  4. Return — never raises to the HTTP layer.
"""

import structlog

from app.schemas.sos import (
    NotifiedGuardian,
    SOSLocation,
    SOSRequest,
    SOSResponseV2,
)
from app.services.sos_service import create_sos_alert_v2

logger = structlog.get_logger(__name__)


class SOSAgent:
    """Orchestrates the full SOS + guardian notification pipeline."""

    async def run(self, req: SOSRequest) -> SOSResponseV2:
        logger.info(
            "SOSAgent started",
            user=req.user_name,
            risk_level=req.risk_level,
            safety_score=req.safety_score,
            latitude=req.latitude,
            longitude=req.longitude,
        )

        try:
            alert = await create_sos_alert_v2(req)
        except RuntimeError as exc:
            logger.error("SOSAgent: service failure", user=req.user_name, error=str(exc))
            raise

        timestamp_str = alert.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        notified = [
            NotifiedGuardian(
                id=g["id"],
                name=g["name"],
                phone=g["phone"],
                relation=g["relation"],
                notification_status=g["notification_status"],
            )
            for g in alert.guardians_notified
        ]

        logger.info(
            "SOSAgent complete",
            alert_id=alert.alert_id,
            user=alert.user_name,
            guardian_count=len(notified),
        )

        return SOSResponseV2(
            status="success",
            alert_id=alert.alert_id,
            timestamp=timestamp_str,
            message=(
                f"SOS alert dispatched. "
                f"{len(notified)} guardian(s) notified."
            ),
            user_name=alert.user_name,
            risk_level=alert.risk_level,  # type: ignore[arg-type]
            safety_score=alert.safety_score,
            location=SOSLocation(
                latitude=alert.latitude,
                longitude=alert.longitude,
            ),
            guardian_count=len(notified),
            guardians_notified=notified,
        )
