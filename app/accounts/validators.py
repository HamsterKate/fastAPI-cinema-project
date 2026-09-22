import re
from typing import Annotated

from pydantic import AfterValidator, EmailStr


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    if not re.search(r"[A-Z]", password):
        raise ValueError(
            "Password must contain at least one uppercase letter."
        )

    if not re.search(r"[a-z]", password):
        raise ValueError(
            "Password must contain at least one lowercase letter."
        )

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")

    if not re.search(r"[^\w\s]", password):
        raise ValueError(
            "Password must contain at least one special character."
        )

    return password


Password = Annotated[str, AfterValidator(validate_password)]


def normalize_email(email: EmailStr) -> str:
    return str(email).lower()


NormalizedEmail = Annotated[
    EmailStr,
    AfterValidator(normalize_email),
]
