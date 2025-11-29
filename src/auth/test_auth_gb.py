import requests
from src.GalacticBuf_serialization.serialization import (
    GBObject, GBValue, serialize_message
)

BASE = "http://127.0.0.1:8080"

def send(path, obj):
    msg = serialize_message(obj)
    return requests.post(
        BASE + path,
        data=msg,
        headers={"Content-Type": "application/x-galacticbuf"}
    )

# ----------------------------------
print("TEST 1: Register user")
user = GBObject([
    ("username", GBValue.make_string("bob")),
    ("password", GBValue.make_string("secret")),
])
res = send("/register", user)
print("Status:", res.status_code)   # Expect 204

# ----------------------------------
print("TEST 2: Register again (should conflict)")
res = send("/register", user)
print("Status:", res.status_code)   # Expect 409

# ----------------------------------
print("TEST 3: Login")
login = GBObject([
    ("username", GBValue.make_string("bob")),
    ("password", GBValue.make_string("secret")),
])
res = send("/login", login)
print("Status:", res.status_code)   # Expect 200
print("Raw Token Output:", res.content)  # GB encoded response
