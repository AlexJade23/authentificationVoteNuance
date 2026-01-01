import hashlib
import secrets
import hmac
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from app.config import get_settings


class CryptoService:
    """Service de cryptographie pour le chiffrement et le hachage."""

    def __init__(self):
        settings = get_settings()
        self._encryption_key = self._derive_key(settings.encryption_key)
        self._fernet = Fernet(self._encryption_key)

    def _derive_key(self, password: str) -> bytes:
        """Dérive une clé de chiffrement à partir d'un mot de passe."""
        salt = b"auth-service-salt-v1"  # Salt fixe pour cohérence
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def hash_email(self, email: str) -> str:
        """Hash un email pour le lookup (SHA256)."""
        normalized = email.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def hash_token(self, token: str) -> str:
        """Hash un token pour le stockage (SHA256)."""
        return hashlib.sha256(token.encode()).hexdigest()

    def encrypt(self, data: str) -> bytes:
        """Chiffre des données avec AES-256 (Fernet)."""
        return self._fernet.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        """Déchiffre des données."""
        return self._fernet.decrypt(encrypted_data).decode()

    def generate_token(self, length: int = 32) -> str:
        """Génère un token cryptographiquement sûr."""
        return secrets.token_urlsafe(length)

    def generate_code(self, length: int = 6) -> str:
        """Génère un code alphanumérique (sans caractères ambigus)."""
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Sans I, O, 0, 1
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_recovery_codes(self, count: int = 10) -> list[str]:
        """Génère des codes de récupération."""
        codes = []
        for _ in range(count):
            # Format: XXXX-XXXX-XXXX-XXXX
            parts = [self.generate_code(4) for _ in range(4)]
            codes.append("-".join(parts))
        return codes

    def constant_time_compare(self, a: str, b: str) -> bool:
        """Comparaison en temps constant pour éviter les timing attacks."""
        return hmac.compare_digest(a.encode(), b.encode())


# Instance singleton
crypto_service = CryptoService()
