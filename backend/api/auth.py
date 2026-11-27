from __future__ import annotations

from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.rate_limit import client_ip_from_request, rate_limiter
from backend.core.security import (
    create_access_token,
    get_current_user,
    get_current_user_and_token,
    hash_password,
    revoke_session_token,
    verify_password,
)
from backend.database.session import get_db
from backend.models.user import AutonomySetting, User
from backend.schemas.auth import (
    AuthTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserProfileResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _ensure_autonomy_setting(db: Session, user: User) -> AutonomySetting:
    setting = db.query(AutonomySetting).filter(AutonomySetting.user_id == user.id).first()
    if setting is None:
        setting = AutonomySetting(
            user_id=user.id,
            default_mode=user.default_autonomy_mode,
            adaptive_enabled=user.adaptive_autonomy_enabled,
            require_plan_approval=user.require_plan_approval,
            require_high_risk_approval=True,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def _serialize_profile(db: Session, user: User) -> UserProfileResponse:
    setting = _ensure_autonomy_setting(db, user)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        default_autonomy_mode=user.default_autonomy_mode,
        adaptive_autonomy_enabled=user.adaptive_autonomy_enabled,
        ml_recommendations_enabled=setting.ml_recommendations_enabled,
        training_consent_opt_in=setting.training_consent_opt_in,
        require_plan_approval=user.require_plan_approval,
        require_high_risk_approval=True,
        theme_preference=user.theme_preference,
        notifications_enabled=user.notifications_enabled,
        created_at=user.created_at,
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"auth_register:{ip}", settings.auth_rate_limit_per_min)

    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.add(AutonomySetting(user_id=user.id))
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user.id,
        user.email,
        db=db,
        user_agent=request.headers.get("user-agent", ""),
        ip_address=ip,
    )
    return AuthTokenResponse(access_token=token, user=_serialize_profile(db, user))


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"auth_login:{ip}", settings.auth_rate_limit_per_min)

    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        user.id,
        user.email,
        db=db,
        user_agent=request.headers.get("user-agent", ""),
        ip_address=ip,
    )
    return AuthTokenResponse(access_token=token, user=_serialize_profile(db, user))


@router.post("/logout")
def logout(
    pair: Tuple[User, str] = Depends(get_current_user_and_token),
    db: Session = Depends(get_db),
) -> dict:
    _user, raw_token = pair
    revoked = revoke_session_token(db, raw_token)
    return {"status": "signed_out", "session_revoked": revoked}


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    return _serialize_profile(db, current_user)


@router.patch("/me", response_model=UserProfileResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    setting = _ensure_autonomy_setting(db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "full_name" and value is not None:
            current_user.full_name = value.strip()
        elif field == "ml_recommendations_enabled" and value is not None:
            setting.ml_recommendations_enabled = value
        elif field == "training_consent_opt_in" and value is not None:
            setting.training_consent_opt_in = value
        elif field == "require_high_risk_approval":
            # Safety invariant: high-risk approval remains locked on
            current_user.require_high_risk_approval = True
            setting.require_high_risk_approval = True
        elif hasattr(current_user, field):
            setattr(current_user, field, value)
            if field == "default_autonomy_mode":
                setting.default_mode = value
            elif field == "adaptive_autonomy_enabled":
                setting.adaptive_enabled = value
            elif field == "require_plan_approval":
                setting.require_plan_approval = value

    db.add(current_user)
    db.add(setting)
    db.commit()
    db.refresh(current_user)
    return _serialize_profile(db, current_user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ip = client_ip_from_request(request)
    rate_limiter.check(f"auth_pw:{ip}", settings.auth_rate_limit_per_min)

    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
    return {"status": "password_updated"}


@router.get("/system-info")
def system_info() -> dict:
    mode, provider_name = settings.active_provider_info
    return {
        "product_name": "VYRO-X",
        "tagline": "Human Intelligence. Agent Evolution.",
        "provider_mode": mode,
        "provider_name": provider_name,
        "database_dialect": "sqlite" if settings.database_url.startswith("sqlite") else "postgresql",
        "demo_notice": (
            "Running in clearly labelled Deterministic Demo Mode (no external LLM API key configured)."
            if mode == "demo"
            else f"Running in Live AI Mode using {provider_name}."
        ),
    }
