import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from app.config import get_settings


class TOTPService:
    """Service de gestion TOTP (Time-based One-Time Password)."""

    def __init__(self):
        self.settings = get_settings()
        self.issuer = self.settings.totp_issuer

    def generate_secret(self) -> str:
        """Génère un secret TOTP (base32)."""
        return pyotp.random_base32()

    def get_totp(self, secret: str) -> pyotp.TOTP:
        """Crée un objet TOTP."""
        return pyotp.TOTP(secret)

    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Vérifie un code TOTP.
        window=1 permet une tolérance de ±30 secondes.
        """
        totp = self.get_totp(secret)
        return totp.verify(code, valid_window=window)

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """Génère l'URI de provisioning pour les apps authenticator."""
        totp = self.get_totp(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.issuer)

    def generate_qr_code_base64(self, provisioning_uri: str) -> str:
        """Génère un QR code en base64 pour l'affichage."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode()

    def get_current_code(self, secret: str) -> str:
        """Obtient le code TOTP actuel (pour debug/test)."""
        totp = self.get_totp(secret)
        return totp.now()


# Instance singleton
totp_service = TOTPService()
