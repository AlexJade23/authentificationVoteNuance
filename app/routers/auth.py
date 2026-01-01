from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from passlib.hash import bcrypt

from app.database import get_db
from app.models.auth import AuthUser, AuthToken, AuthRecoveryCode
from app.schemas.auth import (
    AuthRequest,
    AuthVerifyCode,
    AuthTOTPVerify,
    AuthTOTPSetupResponse,
    AuthTOTPConfirm,
    AuthRecoveryRequest,
    TokenResponse,
    MessageResponse,
)
from app.services.crypto import crypto_service
from app.services.token import token_service
from app.services.email import email_service
from app.services.totp import totp_service
from app.utils.security import get_current_user, get_session_user, limiter
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/request", response_model=MessageResponse)
@limiter.limit("5/hour")
async def request_auth(
    request: Request,
    data: AuthRequest,
    db: Session = Depends(get_db)
):
    """
    Demande d'authentification par magic link.
    Envoie un email avec un lien et un code.
    """
    email_hash = crypto_service.hash_email(data.email)

    # Cherche ou crée l'utilisateur
    user = db.query(AuthUser).filter(AuthUser.email_hash == email_hash).first()

    if not user:
        # Nouvel utilisateur
        user = AuthUser(
            email_hash=email_hash,
            email_encrypted=crypto_service.encrypt(data.email),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Invalide les anciens tokens
    db.query(AuthToken).filter(
        AuthToken.user_id == user.id,
        AuthToken.used_at.is_(None)
    ).delete()

    # Génère nouveau token et code
    token = crypto_service.generate_token(32)
    code = crypto_service.generate_code(6)

    auth_token = AuthToken(
        user_id=user.id,
        token_hash=crypto_service.hash_token(token),
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.magic_link_expire_minutes)
    )
    db.add(auth_token)
    db.commit()

    # Envoie l'email
    await email_service.send_magic_link(data.email, token, code)

    # Réponse identique que l'utilisateur existe ou non (anti-enumeration)
    return MessageResponse(message="Si ce compte existe, un email a été envoyé")


@router.get("/verify/{token}")
async def verify_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Vérifie un magic link token.
    Redirige vers l'application ou la page TOTP.
    """
    token_hash = crypto_service.hash_token(token)

    auth_token = db.query(AuthToken).filter(
        AuthToken.token_hash == token_hash,
        AuthToken.used_at.is_(None),
        AuthToken.expires_at > datetime.utcnow()
    ).first()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalide ou expiré"
        )

    user = auth_token.user

    # Marque le token comme utilisé
    auth_token.used_at = datetime.utcnow()

    # Met à jour les stats utilisateur
    user.last_login_at = datetime.utcnow()
    user.login_count += 1
    db.commit()

    if user.totp_enabled:
        # Génère un token de session temporaire pour le flow MFA
        session_token = token_service.create_session_token(user.public_id)
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/totp?session={session_token}",
            status_code=302
        )

    # Pas de MFA, génère le token final
    access_token = token_service.create_access_token(user.public_id, mfa_verified=False)
    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={access_token}",
        status_code=302
    )


@router.post("/verify-code", response_model=TokenResponse)
@limiter.limit("10/hour")
async def verify_code(
    request: Request,
    data: AuthVerifyCode,
    db: Session = Depends(get_db)
):
    """
    Vérifie un code magic link (alternative au clic sur le lien).
    """
    email_hash = crypto_service.hash_email(data.email)
    user = db.query(AuthUser).filter(AuthUser.email_hash == email_hash).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code invalide ou expiré"
        )

    # Cherche le token avec ce code
    auth_token = db.query(AuthToken).filter(
        AuthToken.user_id == user.id,
        AuthToken.code == data.code.upper(),
        AuthToken.used_at.is_(None),
        AuthToken.expires_at > datetime.utcnow()
    ).first()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code invalide ou expiré"
        )

    # Marque le token comme utilisé
    auth_token.used_at = datetime.utcnow()

    # Met à jour les stats
    user.last_login_at = datetime.utcnow()
    user.login_count += 1
    db.commit()

    if user.totp_enabled:
        # Génère un token de session pour le flow MFA
        session_token = token_service.create_session_token(user.public_id)
        return TokenResponse(
            access_token=session_token,
            expires_in=900,  # 15 minutes
            requires_totp=True
        )

    # Pas de MFA
    access_token = token_service.create_access_token(user.public_id, mfa_verified=False)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_days * 24 * 3600,
        requires_totp=False
    )


@router.post("/totp", response_model=TokenResponse)
@limiter.limit("5/15minutes")
async def verify_totp(
    request: Request,
    data: AuthTOTPVerify,
    user: AuthUser = Depends(get_session_user),
    db: Session = Depends(get_db)
):
    """
    Vérifie le code TOTP pour compléter l'authentification MFA.
    """
    if not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP non activé"
        )

    secret = crypto_service.decrypt(user.totp_secret_encrypted)

    if not totp_service.verify_code(secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code TOTP invalide"
        )

    # Génère le token final avec MFA vérifié
    access_token = token_service.create_access_token(user.public_id, mfa_verified=True)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_days * 24 * 3600,
        requires_totp=False
    )


@router.post("/totp/setup", response_model=AuthTOTPSetupResponse)
async def setup_totp(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configure le TOTP pour l'utilisateur.
    Retourne le secret, QR code et codes de récupération.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP déjà activé"
        )

    # Génère le secret
    secret = totp_service.generate_secret()

    # Récupère l'email pour le QR code
    email = crypto_service.decrypt(user.email_encrypted) if user.email_encrypted else "user"

    # Génère l'URI et le QR code
    provisioning_uri = totp_service.get_provisioning_uri(secret, email)

    # Génère les codes de récupération
    recovery_codes = crypto_service.generate_recovery_codes(10)

    # Stocke temporairement le secret (sera confirmé à l'étape suivante)
    user.totp_secret_encrypted = crypto_service.encrypt(secret)
    db.commit()

    return AuthTOTPSetupResponse(
        secret=secret,
        qr_uri=provisioning_uri,
        recovery_codes=recovery_codes
    )


@router.post("/totp/confirm", response_model=MessageResponse)
async def confirm_totp(
    data: AuthTOTPConfirm,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirme l'activation du TOTP en vérifiant un code.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP déjà activé"
        )

    if not user.totp_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez d'abord configurer le TOTP"
        )

    secret = crypto_service.decrypt(user.totp_secret_encrypted)

    if not totp_service.verify_code(secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code TOTP invalide"
        )

    # Active le TOTP
    user.totp_enabled = True
    db.commit()

    # Notification email
    if user.email_encrypted:
        email = crypto_service.decrypt(user.email_encrypted)
        await email_service.send_totp_enabled(email)

    return MessageResponse(message="Authentification à deux facteurs activée")


@router.post("/totp/disable", response_model=MessageResponse)
async def disable_totp(
    data: AuthTOTPVerify,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Désactive le TOTP (nécessite un code valide).
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP non activé"
        )

    secret = crypto_service.decrypt(user.totp_secret_encrypted)

    if not totp_service.verify_code(secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code TOTP invalide"
        )

    user.totp_enabled = False
    user.totp_secret_encrypted = None

    # Supprime les codes de récupération
    db.query(AuthRecoveryCode).filter(AuthRecoveryCode.user_id == user.id).delete()
    db.commit()

    return MessageResponse(message="Authentification à deux facteurs désactivée")


@router.post("/totp/recovery", response_model=TokenResponse)
async def use_recovery_code(
    data: AuthRecoveryRequest,
    user: AuthUser = Depends(get_session_user),
    db: Session = Depends(get_db)
):
    """
    Utilise un code de récupération pour se connecter sans TOTP.
    """
    # Cherche un code de récupération valide
    recovery_codes = db.query(AuthRecoveryCode).filter(
        AuthRecoveryCode.user_id == user.id,
        AuthRecoveryCode.used_at.is_(None)
    ).all()

    valid_code = None
    for rc in recovery_codes:
        if bcrypt.verify(data.recovery_code.replace("-", ""), rc.code_hash):
            valid_code = rc
            break

    if not valid_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de récupération invalide"
        )

    # Marque comme utilisé
    valid_code.used_at = datetime.utcnow()
    db.commit()

    # Compte les codes restants
    remaining = db.query(AuthRecoveryCode).filter(
        AuthRecoveryCode.user_id == user.id,
        AuthRecoveryCode.used_at.is_(None)
    ).count()

    # Génère le token final
    access_token = token_service.create_access_token(user.public_id, mfa_verified=True)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_days * 24 * 3600,
        requires_totp=False
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    user: AuthUser = Depends(get_current_user)
):
    """
    Déconnexion (supprime le cookie si présent).
    """
    response.delete_cookie("access_token")
    return MessageResponse(message="Déconnexion réussie")
