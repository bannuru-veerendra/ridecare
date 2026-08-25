import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.utils.security import normalize_email, validate_password_strength


class UserResponse(BaseModel):
    """Public user fields returned by the API (no password)"""
    id: uuid.UUID
    email: EmailStr
    full_name: str
    email_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """Request body for PATCH /users/me"""
    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return cleaned

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr | None) -> EmailStr | None:
        if value is None:
            return None
        return normalize_email(value)

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.full_name is None and self.email is None:
            raise ValueError("At least one of full_name or email must be provided")
        return self


class PasswordUpdate(BaseModel):
    """Request body for PATCH /users/me/password"""
    current_password: str
    new_password: str = Field(min_length=8)
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        return self

    @model_validator(mode="after")
    def new_different_from_current(self):
        if self.new_password == self.current_password:
            raise ValueError("New password cannot be the same as the current password")
        return self
