import requests
from EnergyHack25.src.GalacticBuf_serialization.serialization import encode_galacticbuf, decode_galacticbuf

BASE = "http://127.0.0.1:8000"

# --- Test Register ---
register_body = encode_galacticbuf({
    "username": "alice",
    "password": "secret123"
})

r = requests.post(
    BASE + "/register",
    data=register_body,
    headers={"Content-Type": "application/x-galacticbuf"}
)

print("REGISTER status:", r.status_code)  # should be 204


# --- Test Login ---
login_body = encode_galacticbuf({
    "username": "alice",
    "password": "secret123"
})

r = requests.post(
    BASE + "/login",
    data=login_body,
    headers={"Content-Type": "application/x-galacticbuf"}
)

print("LOGIN status:", r.status_code)  # should be 200
print("Raw response bytes:", r.content)

decoded = decode_galacticbuf(r.content)
print("Decoded response:", decoded)
