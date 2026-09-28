from email.message import EmailMessage

import aiosmtplib
from urllib.parse import urlencode

from app.core.config import settings


async def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
    )


async def send_activation_email(
    recipient: str,
    token: str,
) -> None:
    activation_link = f"{settings.activation_url}?" f"{urlencode({'token': token})}"

    body = (
        "Welcome to Cinema 2.0!\n\n"
        "Please activate your account using the link below:\n"
        f"{activation_link}\n\n"
        f"This link expires in {settings.activation_token_expire_minutes} minutes."
    )

    await send_email(
        recipient=recipient,
        subject="Cinema 2.0 — Activate your account",
        body=body,
    )


async def send_password_reset_email(
    recipient: str,
    token: str,
) -> None:
    reset_link = f"{settings.password_reset_url}?" f"{urlencode({'token': token})}"

    body = (
        "You requested a password reset for your Cinema 2.0 account.\n\n"
        "Use the link below to set a new password:\n"
        f"{reset_link}\n\n"
        f"This link expires in "
        f"{settings.password_reset_token_expire_minutes} minutes.\n\n"
        "If you did not request a password reset, "
        "you can safely ignore this email."
    )

    await send_email(
        recipient=recipient,
        subject="Cinema 2.0 — Reset your password",
        body=body,
    )
