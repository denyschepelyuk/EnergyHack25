from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from src.GalacticBuf_serialization.serialization import (
    GBObject, GBValue, serialize_message
)
from src.auth.storage import UserStorage
from src.auth.tokens import TokenManager

app = FastAPI()

storage = UserStorage()
tokens = TokenManager()


async def parse_galacticbuf(request: Request):
    body = await request.body()

    if len(body) < 4:
        raise ValueError("Invalid GalacticBuf message")

    version = body[0]
    if version != 0x01:
        raise ValueError("Wrong GB version")

    field_count = body[1]
    idx = 4 

    output = {}

    for _ in range(field_count):
        name_len = body[idx]
        idx += 1

        name = body[idx:idx + name_len].decode("utf-8")
        idx += name_len

        field_type = body[idx]
        idx += 1

        if field_type == 0x01:
            val = int.from_bytes(body[idx:idx + 8], "big", signed=True)
            idx += 8
            output[name] = val

        elif field_type == 0x02:
            str_len = int.from_bytes(body[idx:idx + 2], "big")
            idx += 2
            val = body[idx:idx + str_len].decode("utf-8")
            idx += str_len
            output[name] = val

        else:
            raise ValueError("Unsupported type in this mission")

    return output


@app.post("/register")
async def register(request: Request):
    try:
        data = await parse_galacticbuf(request)
    except:
        return Response(status_code=400)

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return Response(status_code=400)

    if not storage.add_user(username, password):
        return Response(status_code=409)

    return Response(status_code=204)


@app.post("/login")
async def login(request: Request):
    try:
        data = await parse_galacticbuf(request)
    except:
        return Response(status_code=400)

    username = data.get("username")
    password = data.get("password")

    if not storage.validate_user(username, password):
        return Response(status_code=401)

    token = tokens.generate(username)

    obj = GBObject([
        ("token", GBValue.make_string(token))
    ])
    message = serialize_message(obj)

    return Response(
        content=message,
        media_type="application/x-galacticbuf",
        status_code=200
    )
