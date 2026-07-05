"""
SMTP email sending via aiosmtplib (true async, works with Gmail or any custom SMTP server).
"""
from email.message import EmailMessage

import aiosmtplib

from config import Config


class EmailSendError(Exception):
    """Raised when an email fails to send, with a human-readable reason."""


def build_signature(config: Config) -> str:
    """Build the fixed contact signature block appended to every email body.

    Built in code (not by the LLM) so the exact contact details are always
    guaranteed to be correct, regardless of what the model generates.
    """
    return (
        f"\n\n---\n"
        f"{config.contact_name}\n"
        f"{config.contact_role}\n"
        f"Founder portfolio link: {config.contact_portfolio}\n"
        f"Email: {config.contact_email}\n"
        f"Phone: {config.contact_phone}"
    )


async def send_email(config: Config, recipient: str, subject: str, body: str) -> None:
    """Send an email via SMTP. Raises EmailSendError with a readable reason on failure."""
    message = EmailMessage()
    message["From"] = f"{config.sender_name} <{config.sender_email}>"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            start_tls=config.smtp_use_tls,
        )
    except aiosmtplib.SMTPAuthenticationError as exc:
        raise EmailSendError(f"SMTP Authentication Error: {exc}") from exc
    except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPConnectTimeoutError) as exc:
        raise EmailSendError(f"SMTP Connection Error: {exc}") from exc
    except Exception as exc:
        raise EmailSendError(f"Failed to send email: {exc}") from exc
