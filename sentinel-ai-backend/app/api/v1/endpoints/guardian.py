from fastapi import APIRouter, HTTPException, status

from app.agents.guardian_agent import GuardianAgent
from app.schemas.guardian import GuardianCreate, GuardianResponse, GuardianUpdate

router = APIRouter(prefix="/guardians", tags=["guardians"])


def _agent() -> GuardianAgent:
    return GuardianAgent()


@router.post(
    "",
    response_model=GuardianResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a trusted guardian",
)
async def add_guardian(payload: GuardianCreate) -> GuardianResponse:
    return _agent().add(payload)


@router.get(
    "",
    response_model=list[GuardianResponse],
    status_code=status.HTTP_200_OK,
    summary="List all guardians",
)
async def list_guardians() -> list[GuardianResponse]:
    return _agent().list_all()


@router.get(
    "/{guardian_id}",
    response_model=GuardianResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single guardian",
)
async def get_guardian(guardian_id: str) -> GuardianResponse:
    result = _agent().get_one(guardian_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found")
    return result


@router.put(
    "/{guardian_id}",
    response_model=GuardianResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a guardian",
)
async def update_guardian(guardian_id: str, payload: GuardianUpdate) -> GuardianResponse:
    result = _agent().update(guardian_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found")
    return result


@router.delete(
    "/{guardian_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a guardian",
)
async def delete_guardian(guardian_id: str) -> None:
    deleted = _agent().remove(guardian_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found")
