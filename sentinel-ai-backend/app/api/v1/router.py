from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.guardian import router as guardian_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.risk import router as risk_router
from app.api.v1.endpoints.route import router as route_router
from app.api.v1.endpoints.route_optimization import router as route_optimization_router
from app.api.v1.endpoints.sos import router as sos_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(risk_router)
router.include_router(route_router)
router.include_router(route_optimization_router)
router.include_router(sos_router)
router.include_router(guardian_router)
