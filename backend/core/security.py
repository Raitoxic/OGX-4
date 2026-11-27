from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.database.session import get_db
from backend.models.user import AuthSession, User

bearer_scheme = HTTPBearer(auto_error=False)

PBKDF2_ITERATIONS = 310_000
PBKDF2_DKLEN = 64


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=PBKDF2_DKLEN,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iter_str, salt_hex, expected_hex = stored_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iter_str),
            dklen=len(expected),
        )
        return hmac.compare_digest(derived, expected)
    except Exception:
        return False


def create_access_token(
    user_id: str,
    email: str,
    db: Optional[Session] = None,
    user_agent: str = "",
    ip_address: str = "",
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "email": email,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    if db is not None:
        session_row = AuthSession(
            user_id=user_id,
            token_jti=jti,
            user_agent=(user_agent or "")[:250],
            ip_address=(ip_address or "")[:60],
            issued_at=now,
            expires_at=expire,
        )
        db.add(session_row)
        db.commit()
    return token


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def revoke_session_token(db: Session, token: str) -> bool:
    payload = decode_access_token(token)
    if not payload or not payload.get("jti"):
        return False
    row = db.query(AuthSession).filter(AuthSession.token_jti == payload["jti"]).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True
    return False


def extract_raw_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    query_token: Optional[str],
) -> Optional[str]:
    return credentials.credentials if credentials else query_token


def get_current_user_and_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> Tuple[User, str]:
    raw_token = extract_raw_token(credentials, token)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to VYRO-X.",
        )

    payload = decode_access_token(raw_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )

    jti = payload.get("jti")
    if jti:
        session_row = db.query(AuthSession).filter(AuthSession.token_jti == jti).first()
        if session_row is not None:
            if session_row.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="This session has been signed out. Please sign in again.",
                )
            exp = session_row.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired. Please sign in again.",
                )

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )
    return user, raw_token


def get_current_user(
    pair: Tuple[User, str] = Depends(get_current_user_and_token),
) -> User:
    return pair[0]
