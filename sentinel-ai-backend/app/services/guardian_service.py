"""
GuardianService — in-memory CRUD for trusted emergency contacts.

Version 1 stores guardians in a module-level list protected by a
threading.Lock so it is safe under FastAPI's default thread-pool.

Upgrading to a database (Version 2):
  Replace _store / _lock with SQLAlchemy async session calls.
  Every public function signature stays identical — agents and
  endpoints require zero changes.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.schemas.guardian import GuardianCreate, GuardianRecord, GuardianUpdate

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_store: dict[str, GuardianRecord] = {}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_guardian(data: GuardianCreate) -> GuardianRecord:
    """
    Create a new guardian record.

    If is_primary=True, demote any existing primary guardian first so
    there is always at most one primary contact.
    """
    with _lock:
        if data.is_primary:
            for rec in _store.values():
                if rec.is_primary:
                    rec.is_primary = False
                    rec.updated_at = _now()

        guardian_id = str(uuid.uuid4())
        now = _now()
        record = GuardianRecord(
            id=guardian_id,
            name=data.name,
            phone=data.phone,
            email=data.email,
            relation=data.relation,
            is_primary=data.is_primary,
            created_at=now,
            updated_at=now,
        )
        _store[guardian_id] = record

    logger.info(
        "Guardian created",
        id=guardian_id,
        name=data.name,
        relation=data.relation,
        is_primary=data.is_primary,
    )
    return record


def get_all_guardians() -> list[GuardianRecord]:
    """Return all guardians, primary first then alphabetical."""
    with _lock:
        records = list(_store.values())
    records.sort(key=lambda r: (not r.is_primary, r.name.lower()))
    return records


def get_guardian(guardian_id: str) -> Optional[GuardianRecord]:
    with _lock:
        return _store.get(guardian_id)


def update_guardian(guardian_id: str, data: GuardianUpdate) -> Optional[GuardianRecord]:
    """
    Partial update — only supplied fields are changed.
    Returns None if the guardian does not exist.
    """
    with _lock:
        record = _store.get(guardian_id)
        if record is None:
            return None

        if data.name is not None:
            record.name = data.name.strip()
        if data.phone is not None:
            record.phone = data.phone.strip()
        if data.email is not None:
            record.email = data.email
        if data.relation is not None:
            record.relation = data.relation.strip()
        if data.is_primary is not None:
            if data.is_primary:
                # Demote existing primary
                for other in _store.values():
                    if other.id != guardian_id and other.is_primary:
                        other.is_primary = False
                        other.updated_at = _now()
            record.is_primary = data.is_primary

        record.updated_at = _now()

    logger.info("Guardian updated", id=guardian_id)
    return record


def delete_guardian(guardian_id: str) -> bool:
    """Returns True if deleted, False if not found."""
    with _lock:
        if guardian_id not in _store:
            return False
        del _store[guardian_id]

    logger.info("Guardian deleted", id=guardian_id)
    return True
