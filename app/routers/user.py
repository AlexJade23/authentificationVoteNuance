from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import AuthUser, AuthRecoveryCode, AuthToken, AuthSession
from app.schemas.auth import UserResponse, UserUpdate, MessageResponse
from app.services.crypto import crypto_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/me", tags=["User"])


@router.get("", response_model=UserResponse)
async def get_me(user: AuthUser = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur courant.
    """
    return UserResponse(
        public_id=user.public_id,
        display_name=None,  # Géré par l'application principale
        totp_enabled=user.totp_enabled
    )


@router.patch("", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour le profil utilisateur.
    Note: display_name est géré par l'application principale, pas ici.
    """
    # Le service d'auth ne gère pas le display_name
    # Retourne simplement les infos actuelles
    return UserResponse(
        public_id=user.public_id,
        display_name=data.display_name,
        totp_enabled=user.totp_enabled
    )


@router.delete("", response_model=MessageResponse)
async def delete_me(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprime le compte utilisateur (RGPD - droit à l'oubli).
    Supprime toutes les données associées.
    """
    # Les relations avec cascade suppriment automatiquement:
    # - tokens
    # - recovery_codes
    # - sessions
    db.delete(user)
    db.commit()

    return MessageResponse(message="Compte supprimé avec succès")


@router.get("/sessions")
async def get_sessions(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Liste les sessions actives de l'utilisateur.
    """
    sessions = db.query(AuthSession).filter(
        AuthSession.user_id == user.id
    ).all()

    return [
        {
            "id": str(s.id),
            "ip_address": str(s.ip_address) if s.ip_address else None,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat(),
            "mfa_verified": s.mfa_verified
        }
        for s in sessions
    ]


@router.delete("/sessions", response_model=MessageResponse)
async def revoke_all_sessions(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Révoque toutes les sessions (déconnexion de tous les appareils).
    """
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()

    return MessageResponse(message="Toutes les sessions ont été révoquées")
