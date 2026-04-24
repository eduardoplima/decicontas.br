"""Password hashing and JWT encode/decode.

Transport today: access token in ``Authorization: Bearer …``. Migrating to
HTTP-only cookies is deferred to a later PR per ``backend/CLAUDE.md``.

Refresh tokens are persisted as SHA-256 hashes (not bcrypt) in the
``RefreshTokens`` table. Bcrypt is for low-entropy passwords; a JWT is already
high-entropy, so we only need fast lookup + equality checks. The raw refresh
token is returned to the client once and never logged.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings


# Bcrypt has a 72-byte limit on the password input. Longer passwords used to
# be silently truncated; we reject them explicitly so callers know. Using the
# bcrypt library directly rather than passlib — passlib 1.7.x introspects
# ``bcrypt.__about__`` which bcrypt 5.x removed.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"password exceeds {_BCRYPT_MAX_BYTES} bytes")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        pwd_bytes = password.encode("utf-8")
        if len(pwd_bytes) > _BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _encode(payload: dict[str, Any]) -> str:
    s = get_settings()
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def _decode(token: str) -> dict[str, Any]:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])


def create_access_token(*, user_id: int, role: str) -> str:
    s = get_settings()
    now = _now()
    exp = now + timedelta(minutes=s.jwt_access_token_expire_minutes)
    return _encode(
        {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "jti": uuid.uuid4().hex,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
    )


def create_refresh_token(*, user_id: int) -> tuple[str, datetime]:
    s = get_settings()
    now = _now()
    exp = now + timedelta(days=s.jwt_refresh_token_expire_days)
    token = _encode(
        {
            "sub": str(user_id),
            "type": "refresh",
            "jti": uuid.uuid4().hex,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
    )
    return token, exp.replace(tzinfo=None)


def decode_token(
    token: str, *, expected_type: Literal["access", "refresh"]
) -> dict[str, Any]:
    payload = _decode(token)
    if payload.get("type") != expected_type:
        raise JWTError(
            f"expected token type '{expected_type}', got '{payload.get('type')}'"
        )
    return payload
