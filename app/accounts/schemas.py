from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.accounts.validators import NormalizedEmail, Password


class UserRegistrationSchema(BaseModel):
    email: NormalizedEmail
    password: Password


class UserLoginSchema(BaseModel):
    email: NormalizedEmail
    password: str


class UserResponseSchema(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    is_verified: bool
    group_id: UUID


class UserPasswordChangeSchema(BaseModel):
    old_password: str
    new_password: Password


class PasswordResetRequestSchema(BaseModel):
    email: NormalizedEmail


class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: Password


class ResendActivationSchema(BaseModel):
    email: NormalizedEmail


class TokenRefreshSchema(BaseModel):
    refresh_token: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ForgotPasswordSchema(BaseModel):
    email: NormalizedEmail
