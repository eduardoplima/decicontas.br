"""Low-level tests for ``app.auth.security``: bcrypt + JWT encode/decode."""

from __future__ import annotations

import pytest
from jose import JWTError


def test_hash_and_verify_password_roundtrip() -> None:
    from app.auth.security import hash_password, verify_password

    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert verify_password("correct horse battery staple", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_claims() -> None:
    from app.auth.security import _decode, create_access_token

    token = create_access_token(user_id=42, role="reviewer")
    payload = _decode(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "reviewer"
    assert payload["type"] == "access"
    assert isinstance(payload.get("jti"), str) and len(payload["jti"]) > 0
    assert payload["exp"] > payload["iat"]


def test_refresh_token_claims_and_expiry_returned() -> None:
    from app.auth.security import _decode, create_refresh_token

    token, expires_at = create_refresh_token(user_id=7)
    payload = _decode(token)
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
    assert "role" not in payload
    assert expires_at is not None
    assert payload["exp"] > payload["iat"]


def test_decode_token_rejects_wrong_type() -> None:
    from app.auth.security import create_access_token, decode_token

    access = create_access_token(user_id=1, role="reviewer")
    with pytest.raises(JWTError):
        decode_token(access, expected_type="refresh")


def test_hash_refresh_token_is_deterministic_sha256() -> None:
    from app.auth.security import hash_refresh_token

    a = hash_refresh_token("abc")
    b = hash_refresh_token("abc")
    c = hash_refresh_token("abd")
    assert a == b
    assert a != c
    assert len(a) == 64  # sha256 hex
