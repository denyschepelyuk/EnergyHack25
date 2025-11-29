import hashlib
import os

_users = {}  # username → hashed password (bytes)


def hash_password(password: str) -> bytes:
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        100_000
    )
    return salt + pw_hash


def verify_password(password: str, stored: bytes) -> bool:
    salt = stored[:16]
    expected = stored[16:]
    check = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        100_000
    )
    return check == expected


def user_exists(username: str) -> bool:
    return username in _users


def create_user(username: str, password: str):
    _users[username] = hash_password(password)


def get_user_password(username: str) -> bytes | None:
    return _users.get(username)
