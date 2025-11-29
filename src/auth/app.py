from fastapi import APIRouter, Response, HTTPException
from Galacticbuf_serealization.solution import decode_galacticbuf, encode_galacticbuf

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
    response_buf = encode_galacticbuf({"token": token})

    return Response(
        content=response_buf,
        media_type="application/x-galacticbuf",
        status_code=200
    )
