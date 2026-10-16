import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Securely hash a password."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    try:
        return password_hash.verify(password, hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured.")

    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_MINUTES)

    payload = data.copy()
    payload["iat"] = now
    payload["exp"] = now + expires_delta

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured.")

    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
    )


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return "urumi_" + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Return the SHA-256 hash of an API key."""
    return hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()


def api_key_prefix(api_key: str) -> str:
    """Return a short, non-secret identifier for an API key."""
    return api_key[:12]