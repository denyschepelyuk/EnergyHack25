import requests
from GalacticBuf_serialization.solution import (
    GBObject,
    GBValue,
    serialize_message,
    decode_galacticbuf
)


# Utility: encode dict → GalacticBuf
def encode_gb(data: dict) -> bytes:
    fields = []
    for key, value in data.items():
        if isinstance(value, int):
            fields.append((key, GBValue.make_int(value)))
        else:
            fields.append((key, GBValue.make_string(value)))
    return serialize_message(GBObject(fields))


# Utility: pretty decode response
def try_decode(response_bytes: bytes):
    try:
        decoded = decode_galacticbuf(response_bytes)
        print("Decoded GalacticBuf response:", decoded)
        return decoded
    except Exception:
        print("Response is not valid GalacticBuf or decode failed.")
        return None


BASE = "http://127.0.0.1:8000/auth"


def test_register():
    print("\n=== TEST REGISTER ===")

    payload = encode_gb({
        "username": "testuser",
        "password": "mypassword"
    })

    r = requests.post(
        f"{BASE}/register",
        data=payload,
        headers={"Content-Type": "application/x-galacticbuf"}
    )

    print("Status:", r.status_code)
    print("Raw response:", r.content)

    assert r.status_code in (204, 409), "Registration should succeed or user already exists"


def test_login():
    print("\n=== TEST LOGIN ===")

    payload = encode_gb({
        "username": "testuser",
        "password": "mypassword"
    })

    r = requests.post(
        f"{BASE}/login",
        data=payload,
        headers={"Content-Type": "application/x-galacticbuf"}
    )

    print("Status:", r.status_code)
    print("Raw response:", r.content)

    assert r.status_code == 200, "Login must succeed"

    decoded = try_decode(r.content)
    assert "token" in decoded, "Token must be present in GalacticBuf response"
    print("Token:", decoded["token"])
