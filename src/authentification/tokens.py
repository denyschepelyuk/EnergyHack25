# auth/tokens.py
import hmac
import hashlib
import base64
import time

# Secret key for HMAC signing (you can randomize this if needed)
SECRET_KEY = b"super-secret-key-change-me"


def _sign(data: bytes) -> str:
    """Generate HMAC-SHA256 signature in base64."""
    sig = hmac.new(SECRET_KEY, data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("ascii")


def generate_token(username: str) -> str:
    """
    Generates a token that includes username + timestamp + signature.
    Format: <base64(username)>.<timestamp>.<signature>
    """
    ts = str(int(time.time()))
    username_b64 = base64.urlsafe_b64encode(username.encode("utf-8")).decode("ascii")

    payload = f"{username_b64}.{ts}".encode("utf-8")
    signature = _sign(payload)

    return f"{username_b64}.{ts}.{signature}"


def validate_token(token: str) -> str | None:
    """
    Validates token signature.
    Returns:
        username (string) if valid
        None if invalid
    """
    try:
        username_b64, ts, signature = token.split(".")
    except ValueError:
        return None

    payload = f"{username_b64}.{ts}".encode("utf-8")

    # Recompute expected signature
    expected_sig = _sign(payload)

    if not hmac.compare_digest(signature, expected_sig):
        return None

    # Decode username
    try:
        username = base64.urlsafe_b64decode(username_b64.encode("ascii")).decode("utf-8")
    except Exception:
        return None

    return username
