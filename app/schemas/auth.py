from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class AuthRequest(BaseModel):
    """Demande d'authentification par email."""
    email: EmailStr


class AuthVerifyCode(BaseModel):
    """Vérification du code magic link."""
    email: EmailStr
    code: str


class AuthTOTPVerify(BaseModel):
    """Vérification du code TOTP."""
    code: str


class AuthTOTPSetupResponse(BaseModel):
    """Réponse setup TOTP."""
    secret: str
    qr_uri: str
    recovery_codes: list[str]


class AuthTOTPConfirm(BaseModel):
    """Confirmation activation TOTP."""
    code: str


class AuthRecoveryRequest(BaseModel):
    """Utilisation d'un code de récupération."""
    recovery_code: str


class TokenResponse(BaseModel):
    """Réponse avec token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    requires_totp: bool = False


class MessageResponse(BaseModel):
    """Réponse message simple."""
    message: str


class UserResponse(BaseModel):
    """Informations utilisateur."""
    public_id: UUID
    display_name: Optional[str] = None
    totp_enabled: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Mise à jour profil utilisateur."""
    display_name: Optional[str] = None
