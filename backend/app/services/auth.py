from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import get_settings


def _sign(payload: bytes, secret: bytes) -> str:
    sig = hmac.new(secret, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def create_token(email: str) -> str:
    settings = get_settings()
    secret = (settings.auth_token_secret or "dev-secret").encode()
    now = int(time.time())
    payload = {"email": email, "iat": now, "exp": now + settings.auth_token_ttl_seconds}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    token = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    sig = _sign(payload_bytes, secret)
    return f"{token}.{sig}"


def verify_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    secret = (settings.auth_token_secret or "dev-secret").encode()
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        expected = _sign(payload_bytes, secret)
        if not hmac.compare_digest(expected, sig):
            return None
        payload = json.loads(payload_bytes.decode())
        if int(time.time()) > int(payload.get("exp", 0)):
            return None
        return payload
    except Exception:
        return None


def authenticate_user(email: str, password: str) -> bool:
    settings = get_settings()
    if not settings.auth_user_email or not settings.auth_user_password:
        return False
    return email == settings.auth_user_email and password == settings.auth_user_password
