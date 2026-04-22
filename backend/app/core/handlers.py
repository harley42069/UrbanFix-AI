# app/core/handlers.py

"""
Exception handlers FastAPI → ApiResponse standard
===================================================

Enregistre tous les handlers via ``register_exception_handlers(app)``.
À appeler UNE FOIS dans ``main.py`` après la création de l'instance FastAPI.

Handlers enregistrés :
    - ``StarletteHTTPException``   → http_exception_handler   (4xx/5xx classiques)
    - ``AppError``                 → app_error_handler        (erreurs métier custom)
    - ``RequestValidationError``   → validation_exception_handler (corps invalide Pydantic)
    - ``Exception``                → global_exception_handler (catch-all non géré)

Tous retournent exactement le même format ``ApiResponse``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..schemas.common import ApiError, ApiMeta, ApiResponse, _extract_request_id
from .errors import AppError
from .config import settings

logger = logging.getLogger("urbanfix.api")


# ---------------------------------------------------------------------------
# Mapping HTTP status → code machine
# ---------------------------------------------------------------------------

_HTTP_ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    410: "GONE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


# ---------------------------------------------------------------------------
# Helper interne
# ---------------------------------------------------------------------------


def _build_error_response(
    http_status: int,
    error_code: str,
    message: str,
    details: Any = None,
    request: Request | None = None,
) -> JSONResponse:
    """Construit un JSONResponse avec la structure ApiResponse d'erreur."""
    request_id = _extract_request_id(request)
    body = ApiResponse(
        success=False,
        data=None,
        error=ApiError(code=error_code, message=message, details=details),
        meta=ApiMeta(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(status_code=http_status, content=body.model_dump())


# ---------------------------------------------------------------------------
# Handlers individuels
# ---------------------------------------------------------------------------


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Convertit les ``HTTPException`` FastAPI/Starlette en ``ApiResponse``.
    Couvre toutes les erreurs 4xx/5xx levées par le framework
    (ex: 401 auth manquante, 422 validation schema) ou par les dépendances.
    """
    error_code = _HTTP_ERROR_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
    return _build_error_response(
        exc.status_code,
        error_code,
        str(exc.detail),
        request=request,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Convertit les exceptions ``AppError`` (erreurs métier UrbanFix) en ``ApiResponse``.
    Les erreurs 4xx sont loggées en WARNING, les 5xx en ERROR.
    """
    log = logger.error if exc.status_code >= 500 else logger.warning
    log(
        "AppError [%s] %s — %s",
        _extract_request_id(request),
        exc.error_code,
        exc.message,
    )
    return _build_error_response(
        exc.status_code,
        exc.error_code,
        exc.message,
        exc.details,
        request,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Convertit ``RequestValidationError`` (corps/params invalides per Pydantic)
    en ``ApiResponse`` avec la liste des champs en erreur dans ``details``.
    """
    details = [
        {
            "loc": list(err["loc"]),
            "msg": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    return _build_error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR",
        "Données de requête invalides",
        details=details,
        request=request,
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all pour toutes les exceptions non gérées (erreurs inattendues).
    En mode DEBUG, le message de l'exception est exposé dans la réponse.
    En production, un message générique est retourné.
    """
    logger.exception(
        "Erreur non gérée [%s]: %s",
        _extract_request_id(request),
        exc,
    )
    message = str(exc) if settings.DEBUG else "Erreur interne du serveur"
    return _build_error_response(500, "INTERNAL_ERROR", message, request=request)


# ---------------------------------------------------------------------------
# Registreur principal
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """
    Enregistre les quatre handlers dans l'instance FastAPI.

    Appeler dans ``main.py`` juste après la création de l'app ::

        from app.core.handlers import register_exception_handlers
        app = FastAPI(...)
        register_exception_handlers(app)
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, global_exception_handler)
