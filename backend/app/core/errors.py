# app/core/errors.py

"""
Exceptions personnalisées UrbanFix
====================================

Chaque exception mappe vers un code HTTP + un code machine-readable.
L'``app_error_handler`` dans ``core/handlers.py`` les convertit
automatiquement en ``ApiResponse`` standard.

Exemple d'usage dans un endpoint ::

    from app.core.errors import NotFoundError, ConflictError

    def get_user(user_id: int, db: Session):
        user = db.query(User).get(user_id)
        if not user:
            raise NotFoundError("Utilisateur introuvable")
        return user
"""

from typing import Any


# ---------------------------------------------------------------------------
# Classe de base
# ---------------------------------------------------------------------------


class AppError(Exception):
    """
    Classe de base pour toutes les erreurs applicatives métier.

    Attributs de classe à surcharger dans les sous-classes :
        status_code : Code HTTP de la réponse (ex: 404).
        error_code  : Code machine-readable inclus dans ``ApiError.code``
                      (ex: ``"NOT_FOUND"``).
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({self.message!r})"


# ---------------------------------------------------------------------------
# Sous-classes métier
# ---------------------------------------------------------------------------


class NotFoundError(AppError):
    """
    Ressource introuvable (404).
    Exemples : utilisateur, signalement, estimation inexistants.
    """

    status_code = 404
    error_code = "NOT_FOUND"


class ForbiddenError(AppError):
    """
    Accès refusé (403).
    L'utilisateur est authentifié mais n'a pas les droits nécessaires.
    """

    status_code = 403
    error_code = "FORBIDDEN"


class UnauthorizedError(AppError):
    """
    Non authentifié (401).
    Token absent, invalide ou expiré.
    """

    status_code = 401
    error_code = "UNAUTHORIZED"


class ConflictError(AppError):
    """
    Conflit de ressource (409).
    Exemples : email déjà utilisé, doublon en base.
    """

    status_code = 409
    error_code = "CONFLICT"


class AppValidationError(AppError):
    """
    Erreur de validation métier (422).
    Différent de la validation Pydantic automatique de FastAPI —
    réservé aux règles de gestion (ex: fichier non image, détections absentes).
    """

    status_code = 422
    error_code = "VALIDATION_ERROR"


class ExternalServiceError(AppError):
    """
    Erreur d'un service externe (502 Bad Gateway).
    Exemples : Groq API, SDXL, Bark TTS indisponibles ou en erreur.
    """

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
