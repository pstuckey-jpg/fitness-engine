"""Authentication helpers for email/password accounts."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from .storage import create_user, get_user_by_email


HASH_NAME = "sha256"
ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC using a per-password salt."""
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_{HASH_NAME}${ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
    try:
        algorithm, iterations, salt_hex, derived_hex = password_hash.split("$")
        _, hash_name = algorithm.split("_", 1)
    except ValueError:
        return False

    candidate = hashlib.pbkdf2_hmac(
        hash_name,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(candidate.hex(), derived_hex)


def signup_user(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
    """Create an account, returning (user, error)."""
    email = email.lower().strip()
    if not email or "@" not in email:
        return None, "Enter a valid email."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    if get_user_by_email(email):
        return None, "An account with that email already exists."
    return create_user(email, hash_password(password)), None


def authenticate_user(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
    """Authenticate an account, returning (user, error)."""
    user = get_user_by_email(email.lower().strip())
    if not user or not verify_password(password, user["password_hash"]):
        return None, "Invalid email or password."
    return user, None
