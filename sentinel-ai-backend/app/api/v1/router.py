from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.risk import router as risk_router
from app.api.v1.endpoints.route import router as route_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(risk_router)
router.include_router(route_router)
