# app/api/endpoints/auth.py

"""
Endpoints Authentification
Register, Login, Refresh Token, Logout
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from ...db.session import get_db
from ...models.user import User
from ...schemas.user import UserCreate, UserLogin, UserResponse, Token
from ...schemas.common import ApiResponse, ok
from ...core.errors import ConflictError, ForbiddenError, UnauthorizedError
from ..dependencies import get_current_active_user, get_current_user
from ...core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from ...core.config import settings

router = APIRouter()


# ========== DEPENDENCIES ==========


# ========== ENDPOINTS ==========

@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau compte utilisateur.
    Retourne ``ApiResponse[UserResponse]``.
    """
    if db.query(User).filter(User.email == user_data.email).first():
        raise ConflictError("Email déjà utilisé")

    if db.query(User).filter(User.username == user_data.username).first():
        raise ConflictError("Nom d'utilisateur déjà pris")

    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return ok(UserResponse.model_validate(user), request)


@router.post("/login", response_model=ApiResponse[Token])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Se connecter avec email/username et password.
    Retourne ``ApiResponse[Token]`` avec ``data.access_token``.
    """
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError("Email/username ou mot de passe incorrect")

    if not user.is_active:
        raise ForbiddenError("Compte désactivé")

    access_token = create_access_token(data={
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    })
    refresh_token = create_refresh_token(data={
        "user_id": user.id,
        "email": user.email,
    })

    return ok(
        Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer"),
        request,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Obtenir nouveau access token avec refresh token
    
    Args:
        refresh_token: Refresh token JWT
        db: Session database
        
    Returns:
        Nouveaux tokens
        
    Raises:
        HTTPException 401 si token invalide
    """
    payload = verify_token(refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur invalide"
        )
    
    # Créer nouveaux tokens
    new_access_token = create_access_token(data={
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    })
    
    new_refresh_token = create_refresh_token(data={
        "user_id": user.id,
        "email": user.email
    })
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtenir les informations de l'utilisateur connecté.
    Retourne ``ApiResponse[UserResponse]``.
    """
    return ok(UserResponse.model_validate(current_user), request)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Se déconnecter (invalidation token côté client)
    
    Args:
        current_user: User connecté
        
    Returns:
        Message confirmation
    """
    return {
        "success": True,
        "message": "Déconnexion réussie"
    }
