"""
API Router Configuration
Configure tous les endpoints de l'API UrbanFix AI
"""

from fastapi import APIRouter

from app.api.endpoints import auth, estimation, process, reports, signalements, upload, websocket_endpoint

# Router principal de l'API
api_router = APIRouter()

# ========== AUTHENTIFICATION ==========
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)

# ========== SIGNALEMENTS ==========
api_router.include_router(
    signalements.router,
    prefix="/signalements",
    tags=["signalements"]
)

# ========== IA & ANALYSE ==========

api_router.include_router(
    estimation.router,
    prefix="/estimation",
    tags=["estimation"]
)

# Heavy AI routers are intentionally not imported here to keep the API bootable
# in environments that do not have full ML stacks installed.

# ========== RAPPORTS & EXPORTS ==========
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["reports"]
)

api_router.include_router(
    process.router,
    prefix="/process",
    tags=["process"]
)

# ========== UPLOAD ==========
api_router.include_router(
    upload.router,
    prefix="/upload",
    tags=["upload"]
)

# ========== WEBSOCKET ==========
api_router.include_router(
    websocket_endpoint.router,
    prefix="/ws",
    tags=["websocket"]
)

__all__ = ["api_router"]
