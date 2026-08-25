from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.security import normalize_email, validate_password_strength


class UserCreate(BaseModel):
    """Request body for POST /auth/register"""
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return cleaned

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    """Request body for POST /auth/login"""
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(BaseModel):
    """OAuth2 token body for Swagger `/auth/token` (Bearer authorize)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionResponse(BaseModel):
    """SPA login/refresh ack — credentials are only in httpOnly cookies."""
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Request body for POST /auth/refresh (optional when httpOnly cookie is set)."""
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    """Request body for POST /auth/logout (optional when httpOnly cookie is set)."""
    refresh_token: str | None = None


class VerifyEmailRequest(BaseModel):
    """Request body for POST /auth/verify-email"""
    token: str = Field(min_length=16)


class ResendVerificationRequest(BaseModel):
    """Request body for POST /auth/resend-verification"""
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return normalize_email(value)


class MessageResponse(BaseModel):
    """Generic success message for verification / resend."""
    message: str

