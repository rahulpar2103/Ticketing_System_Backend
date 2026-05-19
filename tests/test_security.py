"""
Unit tests for core security utilities: hashing, verification, JWT tokens.
"""
import pytest
import jwt
from datetime import datetime, timedelta, timezone

from app.core.security import (
    hash_password, verify_password,
    create_access_token, verify_access_token,
)
from app.core.config import settings


# ═══════════════════════════════════════════════════════════════════════════
# Password hashing
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def hashed():
    return hash_password("mysecretpassword")


def test_hash_password_is_not_plain_text(hashed):
    assert hashed != "mysecretpassword"


def test_verify_password_correct_password_returns_true(hashed):
    assert verify_password("mysecretpassword", hashed) is True


@pytest.mark.parametrize("wrong_password", [
    "wrongpassword",
    "MYSECRETPASSWORD",
    "mysecretpasswor",
    "",
    "   ",
])
def test_verify_password_wrong_passwords_return_false(hashed, wrong_password):
    assert verify_password(wrong_password, hashed) is False


def test_different_hashes_for_same_password():
    """bcrypt should produce different salts each time."""
    h1 = hash_password("same_password")
    h2 = hash_password("same_password")
    assert h1 != h2  # different salts
    assert verify_password("same_password", h1)
    assert verify_password("same_password", h2)


# ═══════════════════════════════════════════════════════════════════════════
# JWT tokens
# ═══════════════════════════════════════════════════════════════════════════

def test_create_and_verify_access_token():
    token = create_access_token(data={"sub": "alice"})
    username = verify_access_token(token)
    assert username == "alice"


def test_verify_token_with_missing_sub():
    """Token without 'sub' claim should raise ValueError."""
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(ValueError, match="Invalid token"):
        verify_access_token(token)


def test_verify_expired_token():
    """Expired token should raise ValueError."""
    token = jwt.encode(
        {"sub": "alice", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(ValueError, match="Invalid token"):
        verify_access_token(token)


def test_verify_token_with_wrong_secret():
    token = jwt.encode(
        {"sub": "alice", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        "wrong-secret",
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(ValueError, match="Invalid token"):
        verify_access_token(token)


def test_verify_token_garbage_string():
    with pytest.raises(ValueError, match="Invalid token"):
        verify_access_token("not.a.real.token")


def test_token_contains_expiry():
    token = create_access_token(data={"sub": "alice"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert "exp" in payload