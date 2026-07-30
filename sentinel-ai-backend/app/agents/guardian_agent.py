"""
GuardianAgent — orchestrates guardian CRUD operations.

Intentionally thin: all business logic lives in GuardianService.
The agent's job is to translate service results into API response schemas
and provide a single, testable entry point per operation.
"""

import structlog

from app.schemas.guardian import (
    GuardianCreate,
    GuardianRecord,
    GuardianResponse,
    GuardianUpdate,
)
from app.services.guardian_service import (
    create_guardian,
    delete_guardian,
    get_all_guardians,
    get_guardian,
    update_guardian,
)

logger = structlog.get_logger(__name__)


def _to_response(record: GuardianRecord) -> GuardianResponse:
    return GuardianResponse(
        id=record.id,
        name=record.name,
        phone=record.phone,
        email=record.email,
        relation=record.relation,
        is_primary=record.is_primary,
        created_at=record.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=record.updated_at.strftime("%Y-%m-%dT%H:%M:%S"),
    )


class GuardianAgent:
    """CRUD orchestrator for trusted emergency contacts."""

    def add(self, data: GuardianCreate) -> GuardianResponse:
        logger.info("GuardianAgent: add", name=data.name, relation=data.relation)
        record = create_guardian(data)
        return _to_response(record)

    def list_all(self) -> list[GuardianResponse]:
        records = get_all_guardians()
        logger.info("GuardianAgent: list", count=len(records))
        return [_to_response(r) for r in records]

    def get_one(self, guardian_id: str) -> GuardianResponse | None:
        record = get_guardian(guardian_id)
        if record is None:
            logger.warning("GuardianAgent: not found", id=guardian_id)
            return None
        return _to_response(record)

    def update(self, guardian_id: str, data: GuardianUpdate) -> GuardianResponse | None:
        logger.info("GuardianAgent: update", id=guardian_id)
        record = update_guardian(guardian_id, data)
        if record is None:
            return None
        return _to_response(record)

    def remove(self, guardian_id: str) -> bool:
        logger.info("GuardianAgent: delete", id=guardian_id)
        return delete_guardian(guardian_id)
