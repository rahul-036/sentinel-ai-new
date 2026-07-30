"""
NotificationService — pluggable dispatcher interface.

Architecture
------------
NotificationDispatcher is an abstract base class.  Every concrete
implementation (Twilio SMS, SendGrid Email, WhatsApp Business, Firebase
Push) must implement a single method: dispatch().

The active dispatcher is selected at startup via get_dispatcher().
Swapping providers requires only changing get_dispatcher() — zero
changes to agents, services, or endpoints.

Version 1: SimulatedDispatcher
  Logs a structured message and returns status="simulated".
  No external calls are made.

Adding Twilio SMS (future example):
  class TwilioSMSDispatcher(NotificationDispatcher):
      async def dispatch(self, alert_id, user_name, risk_level,
                         safety_score, latitude, longitude,
                         guardian_name, guardian_phone) -> str:
          client = Client(TWILIO_SID, TWILIO_TOKEN)
          client.messages.create(
              to=guardian_phone,
              from_=TWILIO_FROM,
              body=f"SOS from {user_name} ...",
          )
          return "sent"
"""

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class NotificationDispatcher(ABC):
    """
    One method to implement per channel.

    Returns a status string: "sent" | "simulated" | "failed"
    """

    @abstractmethod
    async def dispatch(
        self,
        *,
        alert_id: str,
        user_name: str,
        risk_level: str,
        safety_score: int,
        latitude: float,
        longitude: float,
        guardian_name: str,
        guardian_phone: str,
        guardian_email: str | None,
    ) -> str:
        ...


# ---------------------------------------------------------------------------
# Version 1: Simulated dispatcher
# ---------------------------------------------------------------------------

class SimulatedDispatcher(NotificationDispatcher):
    """
    Logs a structured notification record and returns "simulated".

    Replace this class with TwilioSMSDispatcher, SendGridDispatcher, etc.
    when real delivery is needed.
    """

    async def dispatch(
        self,
        *,
        alert_id: str,
        user_name: str,
        risk_level: str,
        safety_score: int,
        latitude: float,
        longitude: float,
        guardian_name: str,
        guardian_phone: str,
        guardian_email: str | None,
    ) -> str:
        logger.info(
            "SIMULATED notification dispatched",
            alert_id=alert_id,
            guardian=guardian_name,
            phone=guardian_phone,
            email=guardian_email,
            user=user_name,
            risk_level=risk_level,
            safety_score=safety_score,
            latitude=latitude,
            longitude=longitude,
            channel="simulated",
        )
        return "simulated"


# ---------------------------------------------------------------------------
# Factory — swap this to change the active dispatcher
# ---------------------------------------------------------------------------

_dispatcher: NotificationDispatcher = SimulatedDispatcher()


def get_dispatcher() -> NotificationDispatcher:
    """
    Return the active notification dispatcher.

    To switch to Twilio:
        _dispatcher = TwilioSMSDispatcher(sid=..., token=..., from_=...)

    To switch to SendGrid:
        _dispatcher = SendGridDispatcher(api_key=...)

    No other file needs to change.
    """
    return _dispatcher
