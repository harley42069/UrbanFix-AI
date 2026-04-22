# app/core/security.py

"""
Sécurité et Authentification
Gestion JWT, hashing passwords, vérification tokens
"""

from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

# Configuration hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si password correspond au hash
    
    Args:
        plain_password: Mot de passe clair
        hashed_password: Hash stocké en DB
        
    Returns:
        True si match
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt.
    Tronque à 72 bytes (limite bcrypt) pour éviter l'erreur passlib.
    """
    # bcrypt limite à 72 bytes — tronquer explicitement
    password_bytes = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(password_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un JWT access token
    
    Args:
        data: Données à encoder (user_id, email, etc.)
        expires_delta: Durée validité custom
        
    Returns:
        Token JWT signé
    """
    to_encode = data.copy()
    
    # Définir expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    # Encoder JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Crée un JWT refresh token (validité 7 jours)
    
    Args:
        data: Données à encoder
        
    Returns:
        Refresh token JWT
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Décode et valide un JWT
    
    Args:
        token: JWT à décoder
        
    Returns:
        Payload décodé ou None si invalide
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Vérifie token JWT et son type
    
    Args:
        token: JWT à vérifier
        token_type: Type attendu ("access" ou "refresh")
        
    Returns:
        Payload si valide, None sinon
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    # Vérifier type
    if payload.get("type") != token_type:
        return None
    
    # Vérifier expiration (déjà fait par jwt.decode)
    return payload
