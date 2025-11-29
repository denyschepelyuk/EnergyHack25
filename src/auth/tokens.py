import secrets

_tokens = {}  # token → username


def issue_token(username: str) -> str:
    token = secrets.token_hex(32)
    _tokens[token] = username
    return token


def validate_token(token: str) -> str | None:
    return _tokens.get(token)
