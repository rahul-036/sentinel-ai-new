"""
SOS schemas.

Backward-compatible extension of the original schema.
All existing classes (SOSRequest, SOSLocation, SOSResponse, SOSAlert)
are preserved unchanged so the existing /sos/send contract is unbroken.

New additions:
  - NotifiedGuardian   — one guardian's notification result inside a response
  - SOSResponseV2      — extended response that includes guardian notifications
  - SOSHistoryItem     — one entry in the /sos/history list
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["Low", "Medium", "High", "Critical"]


# ---------------------------------------------------------------------------
# Request  (unchanged)
# ---------------------------------------------------------------------------

class SOSRequest(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100, examples=["Rahul"])
    phone: str = Field(..., examples=["9876543210"])
    latitude: float = Field(..., ge=-90.0, le=90.0, examples=[11.0168])
    longitude: float = Field(..., ge=-180.0, le=180.0, examples=[76.9558])
    safety_score: int = Field(..., ge=0, le=100, examples=[24])
    risk_level: RiskLevel = Field(..., examples=["High"])

    @field_validator("phone")
    @classmethod
    def phone_must_be_digits(cls, v: str) -> str:
        digits = v.strip().lstrip("+")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            raise ValueError("phone must contain 7–15 digits (optional leading +)")
        return v.strip()

    @field_validator("user_name")
    @classmethod
    def user_name_no_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_name must not be blank")
        return v.strip()


# ---------------------------------------------------------------------------
# Location sub-model  (unchanged)
# ---------------------------------------------------------------------------

class SOSLocation(BaseModel):
    latitude: float
    longitude: float


# ---------------------------------------------------------------------------
# Original response  (unchanged — keeps /sos/send backward-compatible)
# ---------------------------------------------------------------------------

class SOSResponse(BaseModel):
    status: str
    alert_id: str
    timestamp: str
    message: str
    user_name: str
    risk_level: RiskLevel
    safety_score: int
    location: SOSLocation


# ---------------------------------------------------------------------------
# New: per-guardian notification result
# ---------------------------------------------------------------------------

class NotifiedGuardian(BaseModel):
    id: str
    name: str
    phone: str
    relation: str
    notification_status: str  # "sent" | "failed" | "simulated"


# ---------------------------------------------------------------------------
# New: extended SOS response (used by the new SOSAgent)
# ---------------------------------------------------------------------------

class SOSResponseV2(BaseModel):
    status: str
    alert_id: str
    timestamp: str
    message: str
    user_name: str
    risk_level: RiskLevel
    safety_score: int
    location: SOSLocation
    guardian_count: int
    guardians_notified: list[NotifiedGuardian] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# New: SOS history item
# ---------------------------------------------------------------------------

class SOSHistoryItem(BaseModel):
    alert_id: str
    timestamp: str
    user_name: str
    latitude: float
    longitude: float
    risk_level: str
    safety_score: int
    guardian_count: int
    guardians_notified: list[NotifiedGuardian] = Field(default_factory=list)
    status: str


# ---------------------------------------------------------------------------
# Internal alert record  (extended — backward-compatible with existing service)
# ---------------------------------------------------------------------------

@dataclass
class SOSAlert:
    alert_id: str
    user_name: str
    phone: str
    latitude: float
    longitude: float
    safety_score: int
    risk_level: str
    timestamp: datetime
    emergency_message: str
    dispatched_channels: list[str] = field(default_factory=list)
    # New fields — default to empty so existing code that creates SOSAlert
    # without these fields continues to work.
    guardians_notified: list[dict] = field(default_factory=list)
