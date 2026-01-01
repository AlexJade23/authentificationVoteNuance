from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models.auth import AuthUser
from app.services.token import token_service

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AuthUser:
    """Récupère l'utilisateur courant depuis le token JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    public_id = token_service.get_public_id_from_token(credentials.credentials)
    if not public_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(AuthUser).filter(AuthUser.public_id == public_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[AuthUser]:
    """Récupère l'utilisateur courant si authentifié, sinon None."""
    if not credentials:
        return None

    public_id = token_service.get_public_id_from_token(credentials.credentials)
    if not public_id:
        return None

    return db.query(AuthUser).filter(AuthUser.public_id == public_id).first()


async def get_session_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AuthUser:
    """
    Récupère l'utilisateur depuis un token de session (pour le flow MFA).
    Accepte les tokens de type 'session'.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de session requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = token_service.verify_token(credentials.credentials)
    if not payload or payload.get("type") != "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de session invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        public_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de session invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(AuthUser).filter(AuthUser.public_id == public_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


class RateLimiter:
    """Helper pour les limites de rate."""

    @staticmethod
    def auth_request():
        """5 requêtes par email par heure."""
        return "5/hour"

    @staticmethod
    def auth_verify():
        """10 tentatives par token par heure."""
        return "10/hour"

    @staticmethod
    def totp_verify():
        """5 tentatives par session par 15 minutes."""
        return "5/15minutes"
