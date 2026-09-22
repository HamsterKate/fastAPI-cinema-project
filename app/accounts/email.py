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
    activation_link = (
        f"{settings.activation_url}?"
        f"{urlencode({'token': token})}"
    )

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
