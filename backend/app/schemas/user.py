# app/shemas/user.py

"""
Schemas Pydantic User
Validation données utilisateurs (input/output API)
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

from ..models.user import UserRole


# ========== SCHEMAS CREATE/UPDATE ==========

class UserCreate(BaseModel):
    """
    Schema création utilisateur (register)
    """
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.CITIZEN


class UserUpdate(BaseModel):
    """
    Schema mise à jour utilisateur
    """
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    """
    Schema login
    """
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    """
    Schema changement mot de passe
    """
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# ========== SCHEMAS RESPONSE ==========

class UserResponse(BaseModel):
    """
    Schema réponse utilisateur (sans password)
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserWithStats(UserResponse):
    """
    Utilisateur avec statistiques
    """
    signalements_count: int = 0
    signalements_completed: int = 0


# ========== SCHEMAS AUTH ==========

class Token(BaseModel):
    """
    Schema token JWT
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Données décodées du token
    """
    user_id: int
    email: EmailStr
    role: UserRole
