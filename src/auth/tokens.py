import secrets

class TokenManager:
    def __init__(self):
        self.tokens = {} 

    def generate(self, username: str) -> str:
        token = secrets.token_hex(16)
        self.tokens[token] = username
        return token

    def validate(self, token: str):
        return self.tokens.get(token)
