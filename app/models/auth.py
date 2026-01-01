import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.database import Base


class AuthUser(Base):
    """Utilisateur authentifié."""
    __tablename__ = "auth_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    email_hash = Column(String(64), unique=True, nullable=False, index=True)
    email_encrypted = Column(LargeBinary, nullable=True)
    totp_secret_encrypted = Column(LargeBinary, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)

    # Relations
    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")
    recovery_codes = relationship("AuthRecoveryCode", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    """Token de magic link."""
    __tablename__ = "auth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    user = relationship("AuthUser", back_populates="tokens")


class AuthRecoveryCode(Base):
    """Code de récupération TOTP."""
    __tablename__ = "auth_recovery_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String(60), nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    user = relationship("AuthUser", back_populates="recovery_codes")


class AuthSession(Base):
    """Session utilisateur."""
    __tablename__ = "auth_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(512), nullable=True)
    mfa_verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    user = relationship("AuthUser", back_populates="sessions")
