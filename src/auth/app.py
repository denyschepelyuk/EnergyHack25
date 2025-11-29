from fastapi import APIRouter, Response, HTTPException

from GalacticBuf_serialization.solution import (
    # For decoding:
    parse_cli_args_to_object,            # BUT we need custom decoder, so we implement it below
    GBObject,
    GBValue,
    serialize_message
)

from .storage import (
    user_exists,
    create_user,
    get_user_password,
    verify_password,
)

from .tokens import (
    issue_token,
)

router = APIRouter()


# ------------------------------------------------------------
# Helper: decode incoming GalacticBuf -> Python dict
# (minimal implementation for our specific auth format)
# ------------------------------------------------------------
def decode_galacticbuf(raw: bytes) -> dict:
    """
    Your serializer encodes messages as:
      0x01 | field_count | total_len | [field blocks...]

    Each field block:
      name_len | name | value

    We decode only simple cases needed for auth:
      - string values
      - int values (for token expiry if needed)
    """

    pos = 0

    if raw[pos] != 0x01:
        raise ValueError("Invalid magic byte")
    pos += 1

    field_count = raw[pos]
    pos += 1

    total_len = (raw[pos] << 8) | raw[pos + 1]
    pos += 2

    result = {}

    for _ in range(field_count):
        name_len = raw[pos]
        pos += 1

        name = raw[pos:pos + name_len].decode("utf-8")
        pos += name_len

        val_type = raw[pos]
        pos += 1

        # INT -------------------------------------------------
        if val_type == GBValue.TYPE_INT:
            # 8 bytes signed big-endian
            num = int.from_bytes(raw[pos:pos + 8], "big", signed=True)
            pos += 8
            result[name] = num

        # STRING ----------------------------------------------
        elif val_type == GBValue.TYPE_STRING:
            strlen = (raw[pos] << 8) | raw[pos + 1]
            pos += 2
            s = raw[pos:pos + strlen].decode("utf-8")
            pos += strlen
            result[name] = s

        else:
            raise ValueError("Unsupported type in decoder")

    return result


# ------------------------------------------------------------
# Helper: encode Python dict -> GalacticBuf
# ------------------------------------------------------------
def encode_galacticbuf(data: dict) -> bytes:
    fields = []

    for key, value in data.items():
        if isinstance(value, int):
            fields.append((key, GBValue.make_int(value)))

        elif isinstance(value, str):
            fields.append((key, GBValue.make_string(value)))

        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    obj = GBObject(fields=fields)
    return serialize_message(obj)


# ============================================================
#  REGISTER
# ============================================================
@router.post("/register")
def register_handler(raw: bytes):
    # Decode request
    try:
        data = decode_galacticbuf(raw)
        username = data["username"]
        password = data["password"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GalacticBuf payload")

    # Validate
    if not username or not password:
        raise HTTPException(status_code=400, detail="Empty username or password")

    if user_exists(username):
        raise HTTPException(status_code=409, detail="Username already exists")

    # Create user
    create_user(username, password)

    return Response(status_code=204)  # No Content


# ============================================================
#  LOGIN
# ============================================================
@router.post("/login")
def login_handler(raw: bytes):
    # Decode request
    try:
        data = decode_galacticbuf(raw)
        username = data["username"]
        password = data["password"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GalacticBuf payload")

    stored_pw = get_user_password(username)
    if stored_pw is None or not verify_password(password, stored_pw):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate token
    token = issue_token(username)

    # Encode GalacticBuf response
    response_buf = encode_galacticbuf({
        "token": token
    })

    return Response(
        content=response_buf,
        media_type="application/x-galacticbuf",
        status_code=200
    )
