from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import jwt, JWTError
from app.config import get_settings


class TokenService:
    """Service de gestion des JWT."""

    def __init__(self):
        self.settings = get_settings()

    def create_access_token(
        self,
        public_id: UUID,
        mfa_verified: bool = False,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Crée un JWT d'accès."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.settings.jwt_expire_days)

        to_encode = {
            "sub": str(public_id),
            "mfa": mfa_verified,
            "iat": datetime.utcnow(),
            "exp": expire,
        }

        return jwt.encode(
            to_encode,
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm
        )

    def create_session_token(
        self,
        public_id: UUID,
        expires_minutes: int = 15
    ) -> str:
        """Crée un token de session temporaire (pour le flow MFA)."""
        expire = datetime.utcnow() + timedelta(minutes=expires_minutes)

        to_encode = {
            "sub": str(public_id),
            "type": "session",
            "iat": datetime.utcnow(),
            "exp": expire,
        }

        return jwt.encode(
            to_encode,
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm
        )

    def verify_token(self, token: str) -> Optional[dict]:
        """Vérifie et décode un JWT."""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except JWTError:
            return None

    def get_public_id_from_token(self, token: str) -> Optional[UUID]:
        """Extrait le public_id d'un token."""
        payload = self.verify_token(token)
        if payload and "sub" in payload:
            try:
                return UUID(payload["sub"])
            except ValueError:
                return None
        return None

    def is_mfa_verified(self, token: str) -> bool:
        """Vérifie si le token a passé la MFA."""
        payload = self.verify_token(token)
        return payload.get("mfa", False) if payload else False


# Instance singleton
token_service = TokenService()
