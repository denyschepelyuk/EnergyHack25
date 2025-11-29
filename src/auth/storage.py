class UserStorage:
    def __init__(self):
        self.users = {}  

    def add_user(self, username: str, password: str):
        if username in self.users:
            return False
        self.users[username] = password
        return True

    def validate_user(self, username: str, password: str):
        return self.users.get(username) == password
