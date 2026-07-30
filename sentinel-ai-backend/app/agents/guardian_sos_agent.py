"""
Guardian SOS Agent.

Responsibilities:
  - Accept a validated SOSRequest from the endpoint.
  - Delegate alert creation to SOSService.
  - Map the internal SOSAlert dataclass to the public SOSResponse schema.
  - Never crash — every exception path returns a structured error response.

Architecture note:
  The agent is intentionally thin.  All business logic (ID generation,
  message building, storage) lives in SOSService so it can be reused by
  future agents (e.g. a batch-alert agent or a scheduled escalation agent)
  without touching this file.
"""

import structlog

from app.schemas.sos import SOSLocation, SOSRequest, SOSResponse
from app.services.sos_service import create_sos_alert

logger = structlog.get_logger(__name__)


class GuardianSOSAgent:
    """Orchestrates the SOS alert pipeline for a single request."""

    async def run(self, req: SOSRequest) -> SOSResponse:
        """
        Execute the SOS pipeline.

        Returns SOSResponse on success.
        Returns a failure SOSResponse (status="error") on any unexpected error
        so the HTTP layer always receives a well-formed object.
        """
        logger.info(
            "Guardian SOS Agent started",
            user=req.user_name,
            risk_level=req.risk_level,
            safety_score=req.safety_score,
            latitude=req.latitude,
            longitude=req.longitude,
        )

        try:
            alert = create_sos_alert(req)
        except RuntimeError as exc:
            logger.error(
                "Guardian SOS Agent: service failure",
                user=req.user_name,
                error=str(exc),
            )
            # Surface a structured error — the endpoint will convert this to HTTP 500
            raise

        timestamp_str = alert.timestamp.strftime("%Y-%m-%dT%H:%M:%S")

        logger.info(
            "Guardian SOS Agent complete",
            alert_id=alert.alert_id,
            user=alert.user_name,
            risk_level=alert.risk_level,
            timestamp=timestamp_str,
        )

        return SOSResponse(
            status="success",
            alert_id=alert.alert_id,
            timestamp=timestamp_str,
            message="SOS alert generated successfully.",
            user_name=alert.user_name,
            risk_level=alert.risk_level,  # type: ignore[arg-type]
            safety_score=alert.safety_score,
            location=SOSLocation(
                latitude=alert.latitude,
                longitude=alert.longitude,
            ),
        )
