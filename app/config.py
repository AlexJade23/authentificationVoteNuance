from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database (REQUIRED - no default)
    database_url: str

    # Security (REQUIRED - no default, must be set in .env)
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    encryption_key: str

    # TOTP
    totp_issuer: str = "DecisionCollective"

    # Email
    smtp_host: str = "smtp.brevo.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "auth@decision-collective.fr"

    # URLs
    base_url: str = "https://auth.decision-collective.fr"
    frontend_url: str = "https://app.decision-collective.fr"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Magic link
    magic_link_expire_minutes: int = 15
    magic_link_code_length: int = 6

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
