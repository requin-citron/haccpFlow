from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role: UserRole = UserRole.OPERATOR


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _require_a_real_change(self) -> UserUpdate:
        if not self.model_fields_set:
            raise ValueError("provide role or is_active")
        if "role" in self.model_fields_set and self.role is None:
            raise ValueError("role cannot be null")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_active cannot be null")
        return self


class UserCreated(UserRead):
    temporary_password: str


class UserPasswordReset(BaseModel):
    temporary_password: str
