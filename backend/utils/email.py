import os
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException


def _smtp_config() -> dict:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        raise HTTPException(
            status_code=500,
            detail="Email sending is not configured on the server (missing SMTP_HOST).",
        )
    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587") or "587"),
        "username": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("SMTP_FROM", "").strip() or os.getenv("SMTP_USER", "").strip(),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").strip().lower() not in ("0", "false", "no"),
    }


def send_email(to_address: str, subject: str, body: str) -> None:
    """Send a plain-text email via SMTP. Raises HTTPException if unconfigured or delivery fails."""
    config = _smtp_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_addr"]
    message["To"] = to_address
    message.set_content(body)

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            if config["use_tls"]:
                server.starttls()
            if config["username"]:
                server.login(config["username"], config["password"])
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not send email. Please try again later.",
        ) from exc


def send_password_reset_email(to_address: str, reset_url: str, ttl_minutes: int) -> None:
    subject = "Reset your Planventure password"
    body = (
        "We received a request to reset your Planventure password.\n\n"
        f"Click the link below to choose a new password (expires in {ttl_minutes} minutes):\n"
        f"{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    send_email(to_address, subject, body)
