import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service d'envoi d'emails."""

    def __init__(self):
        self.settings = get_settings()

    async def send_magic_link(
        self,
        to_email: str,
        token: str,
        code: str
    ) -> bool:
        """Envoie un email avec le magic link et le code."""
        subject = "Connexion à Decision Collective"

        magic_link = f"{self.settings.base_url}/auth/verify/{token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .code {{ font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #2563eb; background: #f3f4f6; padding: 16px 24px; border-radius: 8px; display: inline-block; }}
                .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Connexion à Decision Collective</h1>

                <p>Cliquez sur le bouton ci-dessous pour vous connecter :</p>

                <a href="{magic_link}" class="button">Se connecter</a>

                <p>Ou utilisez ce code sur la page de connexion :</p>

                <div class="code">{code}</div>

                <p class="footer">
                    Ce lien expire dans 15 minutes.<br>
                    Si vous n'avez pas demandé cette connexion, ignorez cet email.
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Connexion à Decision Collective

        Cliquez sur ce lien pour vous connecter :
        {magic_link}

        Ou utilisez ce code : {code}

        Ce lien expire dans 15 minutes.
        Si vous n'avez pas demandé cette connexion, ignorez cet email.
        """

        return await self._send_email(to_email, subject, html_content, text_content)

    async def send_totp_enabled(self, to_email: str) -> bool:
        """Notifie l'activation du TOTP."""
        subject = "Authentification à deux facteurs activée"

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentification à deux facteurs activée</h1>
                <p>L'authentification à deux facteurs a été activée sur votre compte Decision Collective.</p>
                <p>Si vous n'êtes pas à l'origine de cette action, contactez-nous immédiatement.</p>
            </div>
        </body>
        </html>
        """

        text_content = """
        Authentification à deux facteurs activée

        L'authentification à deux facteurs a été activée sur votre compte Decision Collective.
        Si vous n'êtes pas à l'origine de cette action, contactez-nous immédiatement.
        """

        return await self._send_email(to_email, subject, html_content, text_content)

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str
    ) -> bool:
        """Envoie un email via SMTP."""
        if not self.settings.smtp_user or not self.settings.smtp_password:
            logger.warning(f"SMTP non configuré - Email simulé vers {to_email}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Content: {text_content[:200]}...")
            return True

        message = MIMEMultipart("alternative")
        message["From"] = self.settings.smtp_from
        message["To"] = to_email
        message["Subject"] = subject

        message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))

        try:
            # Port 465 = SSL direct (use_tls), Port 587 = STARTTLS (start_tls)
            use_ssl = self.settings.smtp_port == 465
            await aiosmtplib.send(
                message,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_user,
                password=self.settings.smtp_password,
                use_tls=use_ssl,
                start_tls=not use_ssl,
            )
            logger.info(f"Email envoyé à {to_email}")
            return True
        except Exception as e:
            logger.error(f"Erreur envoi email à {to_email}: {e}")
            return False


# Instance singleton
email_service = EmailService()
