from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.accounts.validators import Password


class UserRegistrationSchema(BaseModel):
    email: EmailStr
    password: Password


class UserLoginSchema(BaseModel):
    email: EmailStr
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
    email: EmailStr


class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: Password


class TokenRefreshSchema(BaseModel):
    refresh_token: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
