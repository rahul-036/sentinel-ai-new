from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def register():
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Not implemented — coming in Phase 2"},
    )


@router.post("/login", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def login():
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Not implemented — coming in Phase 2"},
    )
