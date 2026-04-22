"""
UrbanFix AI - Backend Principal
Application FastAPI pour l'analyse et la rénovation intelligente des espaces urbains
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import time
from datetime import datetime

from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.rate_limit import get_rate_limiter
from app.schemas.common import fail
from app.api import api_router

logger = logging.getLogger("urbanfix.access")
rate_limiter = get_rate_limiter(settings.DEV_RATE_LIMIT_REQUESTS_PER_MINUTE)

# Créer l'application FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    UrbanFix AI - Plateforme intelligente de diagnostic et rénovation des espaces urbains
    
    ## Fonctionnalités
    
    * **Détection automatique** - YOLOv8 pour identifier les problèmes urbains
    * **Génération de scénarios** - SDXL pour créer des visualisations de rénovation
    * **Estimation de coûts** - Llama 3.1 pour analyser et estimer les coûts en TND
    * **Narration audio** - Bark TTS pour générer des présentations vocales
    * **Vidéos de transformation** - Stable Video Diffusion pour les animations avant/après
    * **Rapports PDF** - Génération automatique de rapports professionnels
    
    ## WebSocket
    
    * **Mises à jour temps réel** - Suivez la progression des analyses en direct
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "https://urbanfix.tn",
        "*"  # Pour le développement, restreindre en production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware : Request ID + logging corrélé
# ---------------------------------------------------------------------------
# Compat mode note:
#   Les anciens clients qui lisaient directement le payload plat (ex: response["access_token"])
#   doivent désormais lire response["data"]["access_token"].
#   Pour activer un unwrapping automatique vers l'ancien format, envoyez l'en-tête
#   ``X-API-Compat: raw`` — réservé pour une future version du middleware.

@app.middleware("http")
async def request_id_and_logging(request: Request, call_next):
    """
    Middleware combiné :
    1. Lit ou génère un Request-ID unique (X-Request-ID).
    2. L'attache à ``request.state.request_id`` pour les handlers.
    3. Ajoute les headers ``X-Request-ID`` et ``X-Process-Time`` à la réponse.
    4. Logue chaque requête avec le request_id (logging corrélé).
    """
    # 1. Request ID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    # Dev-only rate limit: 60 req/min/IP (configurable)
    if settings.DEBUG and settings.DEV_RATE_LIMIT_ENABLED:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        client_ip = (forwarded_for.split(",")[0].strip() if forwarded_for else None) or (
            request.client.host if request.client else "unknown"
        )
        allowed, retry_after = rate_limiter.check(client_ip)
        if not allowed:
            body = fail(
                code="RATE_LIMITED",
                message="Rate limit dépassé (dev)",
                details={"limit": settings.DEV_RATE_LIMIT_REQUESTS_PER_MINUTE, "window_seconds": 60},
                request=request,
            ).model_dump()
            from fastapi.responses import JSONResponse

            response = JSONResponse(status_code=429, content=body)
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-Request-ID"] = request_id
            return response

    start_time = time.time()

    # 2. Traiter la requête
    response = await call_next(request)

    process_time = time.time() - start_time

    # 3. Headers de corrélation
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}"

    # 4. Log corrélé
    logger.info(
        "[%s] %s %s → %d (%.3fs)",
        request_id[:8],
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    
    return response


# ---------------------------------------------------------------------------
# Exception handlers centralisés (ApiResponse standard)
# ---------------------------------------------------------------------------
register_exception_handlers(app)


# Routes de base
@app.get("/", tags=["root"])
async def root():
    """
    Route racine - Informations sur l'API
    
    Returns:
        Informations de l'API
    """
    return {
        "success": True,
        "data": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "description": "API UrbanFix AI - Analyse intelligente des espaces urbains",
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "health": "/health",
                "api": "/api/v1"
            }
        }
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Statut de santé de l'API
    """
    # Vérifier les répertoires nécessaires
    directories_ok = all([
        Path(settings.UPLOADS_DIR).exists(),
        Path(settings.OUTPUTS_DIR).exists(),
    ])
    
    return {
        "success": True,
        "data": {
            "status": "healthy" if directories_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": settings.VERSION,
            "directories_ok": directories_ok,
            "debug_mode": settings.DEBUG
        }
    }


@app.get("/version", tags=["root"])
async def get_version():
    """
    Récupère la version de l'API
    
    Returns:
        Version de l'API
    """
    return {
        "success": True,
        "data": {
            "version": settings.VERSION,
            "project_name": settings.PROJECT_NAME,
            "environment": "development" if settings.DEBUG else "production"
        }
    }


# Inclure les routers de l'API
app.include_router(
    api_router,
    prefix="/api/v1"
)


# Monter les fichiers statiques (outputs)
outputs_path = Path(settings.OUTPUTS_DIR)
outputs_path.mkdir(parents=True, exist_ok=True)

# Stable dev path requested for media artifacts.
app.mount(
    "/static/outputs",
    StaticFiles(directory=str(outputs_path)),
    name="static-outputs",
)

# Backward compatibility for existing clients.
app.mount(
    "/outputs",
    StaticFiles(directory=str(outputs_path)),
    name="outputs",
)


# Événements de démarrage et arrêt
@app.on_event("startup")
async def startup_event():
    """
    Événement de démarrage de l'application
    """
    print("=" * 70)
    print(f"🚀 {settings.PROJECT_NAME} v{settings.VERSION}")
    print("=" * 70)
    print(f"🌍 Serveur démarré sur http://localhost:8000")
    print(f"📚 Documentation Swagger: http://localhost:8000/docs")
    print(f"📖 Documentation ReDoc: http://localhost:8000/redoc")
    print(f"🔧 Mode Debug: {settings.DEBUG}")
    print("=" * 70)
    
    # Créer les répertoires nécessaires
    directories = [
        settings.UPLOADS_DIR,
        settings.OUTPUTS_DIR,
        settings.TEMP_DIR,
        f"{settings.OUTPUTS_DIR}/detections",
        f"{settings.OUTPUTS_DIR}/scenarios",
        f"{settings.OUTPUTS_DIR}/audio",
        f"{settings.OUTPUTS_DIR}/videos",
        f"{settings.OUTPUTS_DIR}/reports",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Répertoires créés")
    print("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Événement d'arrêt de l'application
    """
    print("=" * 70)
    print("🛑 Arrêt du serveur...")
    
    # Décharger les modèles de la mémoire
    try:
        from app.services import get_orchestrator_service
        orchestrator = get_orchestrator_service()
        orchestrator.unload_all_models()
        print("✅ Modèles déchargés de la mémoire")
    except:
        pass
    
    print("👋 Au revoir!")
    print("=" * 70)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
