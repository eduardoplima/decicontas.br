"""Authentication business logic.

All persistence goes through the injected ``Session``. The router is a thin
adapter that maps HTTP to these calls.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
)
from tools.models import RefreshTokenORM, RoleEnum, UserORM


def _role_value(role: RoleEnum | str) -> str:
    return role.value if isinstance(role, RoleEnum) else str(role)


def authenticate_user(session: Session, username: str, password: str) -> UserORM | None:
    user = session.execute(
        select(UserORM).where(UserORM.username == username)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def _mint_tokens(session: Session, user: UserORM) -> tuple[str, str]:
    access = create_access_token(user_id=user.id, role=_role_value(user.role))
    refresh, expires_at = create_refresh_token(user_id=user.id)
    session.add(
        RefreshTokenORM(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=expires_at,
        )
    )
    return access, refresh


def issue_token_pair(session: Session, user: UserORM) -> tuple[str, str]:
    access, refresh = _mint_tokens(session, user)
    session.commit()
    return access, refresh


def rotate_refresh_token(
    session: Session, refresh_token: str
) -> tuple[UserORM, str, str]:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid refresh token",
        ) from exc

    token_hash = hash_refresh_token(refresh_token)
    row = session.execute(
        select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token revoked or not recognized",
        )
    if row.expires_at <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token expired",
        )

    user = session.get(UserORM, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user inactive or not found",
        )

    row.revoked_at = datetime.utcnow()
    access, new_refresh = _mint_tokens(session, user)
    session.commit()
    return user, access, new_refresh


def logout(session: Session, refresh_token: str) -> None:
    """Revoke the given refresh token. Idempotent — invalid/unknown tokens no-op."""
    try:
        decode_token(refresh_token, expected_type="refresh")
    except JWTError:
        return
    token_hash = hash_refresh_token(refresh_token)
    row = session.execute(
        select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return
    row.revoked_at = datetime.utcnow()
    session.commit()
