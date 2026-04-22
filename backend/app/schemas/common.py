# app/schemas/common.py

"""
Schemas de réponse standard UrbanFix API
=========================================

Tous les endpoints retournent ``ApiResponse[T]``.

Format :
    {
        "success": true | false,
        "data":    <payload ou null>,
        "error":   {"code": "...", "message": "...", "details": ...} | null,
        "meta":    {"request_id": "...", "timestamp": "...", "pagination": ...} | null
    }

Mode compat v0 → v1 :
    Avant        : response["access_token"]
    Maintenant   : response["data"]["access_token"]

    Pour faciliter la migration, les anciens clients peuvent lire ``response.data``
    à la place de ``response`` directement.
    Un futur middleware ``X-API-Compat: raw`` pourra unwrapper ``data`` automatiquement
    (voir ``app/main.py``, section "Compat mode").
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Sous-structures
# ---------------------------------------------------------------------------


class ApiError(BaseModel):
    """Structure d'erreur machine-readable incluse dans ApiResponse."""

    code: str = Field(..., description="Code d'erreur machine-readable (ex: NOT_FOUND)")
    message: str = Field(..., description="Message lisible pour l'utilisateur")
    details: Any | None = Field(
        None,
        description="Informations supplémentaires (champs invalides, trace, etc.)",
    )


class PaginationMeta(BaseModel):
    """Métadonnées de pagination pour les listes."""

    total: int = Field(..., description="Nombre total d'éléments (avant pagination)")
    page: int = Field(..., description="Page courante (1-indexée)")
    page_size: int = Field(..., description="Éléments par page")
    pages: int = Field(..., description="Nombre total de pages")
    has_next: bool = Field(..., description="Il existe une page suivante")
    has_prev: bool = Field(..., description="Il existe une page précédente")


class ApiMeta(BaseModel):
    """Métadonnées attachées à chaque réponse."""

    request_id: str = Field(..., description="Identifiant unique de la requête (X-Request-ID)")
    timestamp: str = Field(..., description="Horodatage ISO 8601 UTC de la réponse")
    pagination: PaginationMeta | None = Field(None, description="Pagination (null si pas une liste)")


# ---------------------------------------------------------------------------
# Enveloppe générique
# ---------------------------------------------------------------------------


class ApiResponse(BaseModel, Generic[T]):
    """
    Enveloppe de réponse standard pour tous les endpoints UrbanFix.

    Usage dans un endpoint ::

        @router.get("/foo", response_model=ApiResponse[FooSchema])
        async def get_foo(request: Request):
            data = ...
            return ok(data, request)

    Compat mode v0 :
        L'ancien format "plat" (ex: ``{"access_token": "..."}`` ) est maintenant
        disponible sous ``response["data"]["access_token"]``.
        Pour migrer progressivement, les clients lèvent d'abord ``response.data``
        puis adaptent leurs accès champ par champ.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = Field(..., description="true si la requête a réussi")
    data: T | None = Field(None, description="Payload de la réponse (null si erreur)")
    error: ApiError | None = Field(None, description="Erreur (null si succès)")
    meta: ApiMeta | None = Field(None, description="Métadonnées de la requête")


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _extract_request_id(request: Any) -> str:
    """Extrait le request_id depuis request.state (injecté par middleware)."""
    if request is None:
        return "N/A"
    state = getattr(request, "state", None)
    return getattr(state, "request_id", "N/A")


def ok(
    data: Any,
    request: Any = None,
    pagination: PaginationMeta | None = None,
) -> ApiResponse:
    """
    Crée une ``ApiResponse`` de succès.

    Args:
        data:       Payload à retourner dans ``data``.
        request:    Objet ``Request`` FastAPI (pour lire le ``request_id``).
        pagination: Métadonnées de pagination optionnelles.

    Returns:
        ``ApiResponse`` avec ``success=True``.
    """
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        meta=ApiMeta(
            request_id=_extract_request_id(request),
            timestamp=datetime.now(timezone.utc).isoformat(),
            pagination=pagination,
        ),
    )


def fail(
    code: str,
    message: str,
    details: Any = None,
    request: Any = None,
) -> ApiResponse:
    """
    Crée une ``ApiResponse`` d'erreur.

    Args:
        code:    Code machine-readable (ex: ``"NOT_FOUND"``).
        message: Message lisible.
        details: Informations supplémentaires optionnelles.
        request: Objet ``Request`` FastAPI.

    Returns:
        ``ApiResponse`` avec ``success=False``.
    """
    return ApiResponse(
        success=False,
        data=None,
        error=ApiError(code=code, message=message, details=details),
        meta=ApiMeta(
            request_id=_extract_request_id(request),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
