# auth/storage.py
import hashlib

# In-memory user database:
# { username: hashed_password }
users = {}


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> bool:
    """
    Register a user.
    Returns:
        True  → user registered
        False → username already exists
    """
    if username in users:
        return False

    users[username] = hash_password(password)
    return True


def validate_credentials(username: str, password: str) -> bool:
    """
    Check whether username exists and password matches.
    """
    if username not in users:
        return False

    return users[username] == hash_password(password)
