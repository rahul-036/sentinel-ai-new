"""
Guardian schemas.

Public API models (Pydantic) are separated from the internal storage
dataclass so the HTTP layer never leaks internal fields.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class GuardianCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Priya"])
    phone: str = Field(..., examples=["9876543210"])
    email: Optional[str] = Field(None, examples=["priya@example.com"])
    relation: str = Field(..., min_length=1, max_length=50, examples=["Sister"])
    is_primary: bool = Field(False)

    @field_validator("phone")
    @classmethod
    def phone_must_be_digits(cls, v: str) -> str:
        digits = v.strip().lstrip("+")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            raise ValueError("phone must contain 7–15 digits (optional leading +)")
        return v.strip()

    @field_validator("name", "relation")
    @classmethod
    def no_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be blank")
        return v.strip()


class GuardianUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    relation: Optional[str] = Field(None, min_length=1, max_length=50)
    is_primary: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def phone_must_be_digits(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        digits = v.strip().lstrip("+")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            raise ValueError("phone must contain 7–15 digits (optional leading +)")
        return v.strip()


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class GuardianResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str]
    relation: str
    is_primary: bool
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Internal record — stored in memory, never serialised directly to HTTP
# ---------------------------------------------------------------------------

@dataclass
class GuardianRecord:
    id: str
    name: str
    phone: str
    email: Optional[str]
    relation: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime
