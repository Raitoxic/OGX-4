from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    default_autonomy_mode: str
    adaptive_autonomy_enabled: bool
    ml_recommendations_enabled: bool = True
    training_consent_opt_in: bool = False
    require_plan_approval: bool
    require_high_risk_approval: bool
    theme_preference: str
    notifications_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    default_autonomy_mode: Optional[Literal["supervised", "balanced", "higher_autonomy"]] = None
    adaptive_autonomy_enabled: Optional[bool] = None
    ml_recommendations_enabled: Optional[bool] = None
    training_consent_opt_in: Optional[bool] = None
    require_plan_approval: Optional[bool] = None
    require_high_risk_approval: Optional[bool] = None
    theme_preference: Optional[Literal["light", "dark", "system"]] = None
    notifications_enabled: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
