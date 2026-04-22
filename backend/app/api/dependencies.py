"""API security dependencies: auth, RBAC, ownership checks."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import verify_token
from ..db.session import get_db
from ..models.signalement import Signalement
from ..models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve authenticated user from JWT access token."""
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Alias explicite pour les routes qui exigent un compte actif."""
    return current_user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve authenticated user when token is present, else allow guest in dev.

    Behavior:
    - Authorization header present: authenticate normally.
    - Authorization absent and ALLOW_GUEST=True: return None (guest).
    - Authorization absent and ALLOW_GUEST=False: raise 401 Not authenticated.
    """
    if token:
        return await get_current_user(token=token, db=db)

    env = str(settings.ENVIRONMENT or "development").lower()
    in_production = env in {"production", "prod"}

    if settings.ALLOW_GUEST and not in_production:
        return None

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(roles: list[str]) -> Callable:
    """Dependency factory enforcing RBAC on endpoint access."""
    allowed = {str(r).lower() for r in roles}

    async def _require_role(current_user: User = Depends(get_current_user)) -> User:
        role_value = getattr(current_user.role, "value", current_user.role)
        if str(role_value).lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes",
            )
        return current_user

    return _require_role


def require_owner_or_admin() -> Callable:
    """Dependency factory: allow only resource owner or admin."""

    async def _owner_or_admin(
        signalement_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> Signalement:
        signalement = (
            db.query(Signalement)
            .filter(Signalement.id == signalement_id, Signalement.is_deleted.is_(False))
            .first()
        )
        if not signalement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Signalement introuvable",
            )

        role_value = getattr(current_user.role, "value", current_user.role)
        is_admin = str(role_value).lower() == "admin"
        if signalement.user_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé",
            )
        return signalement

    return _owner_or_admin
