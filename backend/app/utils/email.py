"""Transactional email via SMTP. Without SMTP config, logs the message (dev/test)."""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(*, to: str, subject: str, html: str, text: str) -> None:
    """Send an email over SMTP, or log the body when SMTP is not configured."""
    if not settings.SMTP_HOST:
        logger.warning(
            "Email NOT sent — set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD "
            "in .env. to=%s subject=%s\n%s",
            to,
            subject,
            text,
        )
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME or None,
        password=settings.SMTP_PASSWORD or None,
        start_tls=settings.SMTP_STARTTLS,
    )
    logger.info("Email sent via SMTP to=%s subject=%s", to, subject)


async def send_verification_email(*, to: str, full_name: str, link: str) -> None:
    subject = "Verify your RideCare email"
    text = (
        f"Hi {full_name},\n\n"
        f"Confirm your RideCare account:\n{link}\n\n"
        f"This link expires in {settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS} hours.\n"
        "If you did not sign up, you can ignore this email.\n"
    )
    html = (
        f"<p>Hi {full_name},</p>"
        f"<p>Confirm your RideCare account:</p>"
        f'<p><a href="{link}">Verify email</a></p>'
        f"<p>This link expires in {settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS} hours.</p>"
        "<p>If you did not sign up, you can ignore this email.</p>"
    )
    await send_email(to=to, subject=subject, html=html, text=text)


async def send_reminder_digest_email(
    *,
    to: str,
    full_name: str,
    dashboard_url: str,
    body_text: str,
    body_html: str,
) -> None:
    subject = "RideCare reminders"
    text = (
        f"Hi {full_name},\n\n"
        f"{body_text}\n\n"
        f"Open your garage: {dashboard_url}\n"
    )
    html = (
        f"<p>Hi {full_name},</p>"
        f"{body_html}"
        f'<p><a href="{dashboard_url}">Open RideCare</a></p>'
    )
    await send_email(to=to, subject=subject, html=html, text=text)
