"""Test password hashing and JWT lifecycle."""
import os
import time

import pytest
from jose import jwt

os.environ.setdefault("SECRET_KEY", "x" * 64)

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_device_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)


def test_password_round_trip():
    pw = "Sup3rSecret!"
    h = hash_password(pw)
    assert h != pw
    assert verify_password(pw, h)
    assert not verify_password("wrong", h)


def test_password_hashes_are_unique():
    pw = "samepass"
    assert hash_password(pw) != hash_password(pw)  # bcrypt salts


def test_access_token_carries_role():
    token = create_access_token("user-123", role="admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_no_role():
    token = create_refresh_token("user-123")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert "role" not in payload


def test_decode_invalid_token():
    with pytest.raises(ValueError):
        decode_token("not-a-real-jwt")


def test_decode_tampered_signature():
    token = create_access_token("user-123", role="admin")
    head, body, _sig = token.split(".")
    forged = f"{head}.{body}.AAAA"
    with pytest.raises(ValueError):
        decode_token(forged)


def test_decode_expired_token():
    expired = jwt.encode(
        {"sub": "u", "type": "access", "exp": int(time.time()) - 60},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(ValueError):
        decode_token(expired)


def test_device_api_key_generation():
    plain1, hashed1 = generate_device_api_key()
    plain2, hashed2 = generate_device_api_key()
    assert plain1 != plain2
    assert hashed1 != hashed2
    assert len(plain1) >= 32
    assert hash_api_key(plain1) == hashed1


def test_hash_api_key_deterministic():
    assert hash_api_key("abc") == hash_api_key("abc")
    assert hash_api_key("abc") != hash_api_key("abd")
