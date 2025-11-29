from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# =========================
#   Core Data Structures
# =========================

@dataclass
class GBList:
    element_type: int               # 0x01, 0x02, or 0x04
    elements: List["GBValue"]


@dataclass
class GBObject:
    fields: List[Tuple[str, "GBValue"]] = field(default_factory=list)

    def get(self, name: str) -> Optional["GBValue"]:
        for k, v in self.fields:
            if k == name:
                return v
        return None


@dataclass
class GBValue:
    TYPE_INT    = 0x01
    TYPE_STRING = 0x02
    TYPE_LIST   = 0x03
    TYPE_OBJECT = 0x04

    type: int
    int_value: int = 0
    string_value: str = ""
    list_value: Optional[GBList] = None
    object_value: Optional[GBObject] = None

    @staticmethod
    def make_int(v: int) -> "GBValue":
        return GBValue(type=GBValue.TYPE_INT, int_value=v)

    @staticmethod
    def make_string(s: str) -> "GBValue":
        return GBValue(type=GBValue.TYPE_STRING, string_value=s)

    @staticmethod
    def make_list(elem_type: int, elems: List["GBValue"]) -> "GBValue":
        return GBValue(type=GBValue.TYPE_LIST, list_value=GBList(elem_type, elems))

    @staticmethod
    def make_object(obj: GBObject) -> "GBValue":
        return GBValue(type=GBValue.TYPE_OBJECT, object_value=obj)


# =========================
#   Low-level helpers
# =========================

def write_u8(buf: bytearray, v: int) -> None:
    buf.append(v & 0xFF)


def write_u16(buf: bytearray, v: int) -> None:
    buf.append((v >> 8) & 0xFF)
    buf.append(v & 0xFF)


def write_i64(buf: bytearray, v: int) -> None:
    # 64-bit signed, big-endian
    if not (-2**63 <= v < 2**63):
        raise ValueError("int64 out of range")
    u = v & ((1 << 64) - 1)
    for shift in range(56, -1, -8):
        buf.append((u >> shift) & 0xFF)


class Buffer:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read_u8(self) -> int:
        if self.pos >= len(self.data):
            raise ValueError("Unexpected EOF while reading u8")
        v = self.data[self.pos]
        self.pos += 1
        return v

    def read_u16(self) -> int:
        if self.pos + 2 > len(self.data):
            raise ValueError("Unexpected EOF while reading u16")
        hi = self.data[self.pos]
        lo = self.data[self.pos + 1]
        self.pos += 2
        return (hi << 8) | lo

    def read_i64(self) -> int:
        if self.pos + 8 > len(self.data):
            raise ValueError("Unexpected EOF while reading i64")
        v = 0
        for _ in range(8):
            v = (v << 8) | self.data[self.pos]
            self.pos += 1
        # Convert from unsigned to signed
        if v & (1 << 63):
            v -= 1 << 64
        return v


# =========================
#   Serialization
# =========================

def write_string_value(buf: bytearray, s: str) -> None:
    b = s.encode("utf-8")
    if len(b) > 65535:
        raise ValueError("String too long")
    write_u16(buf, len(b))
    buf.extend(b)


def write_object_no_header(buf: bytearray, obj: GBObject) -> None:
    if len(obj.fields) > 255:
        raise ValueError("Too many fields in object")
    write_u8(buf, len(obj.fields))
    for name, val in obj.fields:
        name_bytes = name.encode("utf-8")
        if not (1 <= len(name_bytes) <= 255):
            raise ValueError("Invalid field name length")
        write_u8(buf, len(name_bytes))
        buf.extend(name_bytes)
        write_value(buf, val)


def write_list_value(buf: bytearray, lst: GBList) -> None:
    write_u8(buf, lst.element_type)
    if len(lst.elements) > 65535:
        raise ValueError("Too many list elements")
    write_u16(buf, len(lst.elements))

    for el in lst.elements:
        if el.type != lst.element_type:
            raise ValueError("List element type mismatch")
        if el.type == GBValue.TYPE_INT:
            write_i64(buf, el.int_value)
        elif el.type == GBValue.TYPE_STRING:
            write_string_value(buf, el.string_value)
        elif el.type == GBValue.TYPE_OBJECT:
            write_object_no_header(buf, el.object_value)
        else:
            raise ValueError("Unsupported list element type")


def write_value(buf: bytearray, val: GBValue) -> None:
    write_u8(buf, val.type)
    if val.type == GBValue.TYPE_INT:
        write_i64(buf, val.int_value)
    elif val.type == GBValue.TYPE_STRING:
        write_string_value(buf, val.string_value)
    elif val.type == GBValue.TYPE_LIST:
        write_list_value(buf, val.list_value)
    elif val.type == GBValue.TYPE_OBJECT:
        write_object_no_header(buf, val.object_value)
    else:
        raise ValueError("Unknown value type")


def serialize_message(obj: GBObject) -> bytes:
    """
    Serialize a top-level GBObject into a GalacticBuf message (with 4-byte header).
    """
    # Encode body (fields only)
    body = bytearray()
    for name, val in obj.fields:
        name_bytes = name.encode("utf-8")
        if not (1 <= len(name_bytes) <= 255):
            raise ValueError("Invalid field name length")
        write_u8(body, len(name_bytes))
        body.extend(name_bytes)
        write_value(body, val)

    total_len = 4 + len(body)
    if total_len > 65535:
        raise ValueError("Message too large")

    out = bytearray()
    # Header
    write_u8(out, 0x01)              # Protocol version
    write_u8(out, len(obj.fields))   # Field count
    write_u16(out, total_len)        # Total length (includes header)

    out.extend(body)
    return bytes(out)


# =========================
#   Deserialization
# =========================

def read_string_value(b: Buffer) -> str:
    ln = b.read_u16()
    if b.pos + ln > len(b.data):
        raise ValueError("Unexpected EOF while reading string")
    s = b.data[b.pos:b.pos + ln].decode("utf-8")
    b.pos += ln
    return s


def read_list_value(b: Buffer) -> GBList:
    elem_type = b.read_u8()
    if elem_type not in (GBValue.TYPE_INT, GBValue.TYPE_STRING, GBValue.TYPE_OBJECT):
        raise ValueError("Invalid list element type")

    count = b.read_u16()
    elems: List[GBValue] = []

    for _ in range(count):
        if elem_type == GBValue.TYPE_INT:
            v = GBValue.make_int(b.read_i64())
        elif elem_type == GBValue.TYPE_STRING:
            v = GBValue.make_string(read_string_value(b))
        else:  # OBJECT
            v = GBValue.make_object(parse_object_no_header(b))
        elems.append(v)

    return GBList(elem_type, elems)


def read_value(b: Buffer) -> GBValue:
    t = b.read_u8()
    if t == GBValue.TYPE_INT:
        return GBValue.make_int(b.read_i64())
    elif t == GBValue.TYPE_STRING:
        return GBValue.make_string(read_string_value(b))
    elif t == GBValue.TYPE_LIST:
        lst = read_list_value(b)
        return GBValue.make_list(lst.element_type, lst.elements)
    elif t == GBValue.TYPE_OBJECT:
        return GBValue.make_object(parse_object_no_header(b))
    else:
        raise ValueError("Unknown value type while parsing")


def parse_object_no_header(b: Buffer) -> GBObject:
    field_count = b.read_u8()
    obj = GBObject()
    for _ in range(field_count):
        name_len = b.read_u8()
        if name_len == 0:
            raise ValueError("Field name length cannot be zero")
        if b.pos + name_len > len(b.data):
            raise ValueError("Unexpected EOF while reading field name")
        name = b.data[b.pos:b.pos + name_len].decode("utf-8")
        b.pos += name_len

        val = read_value(b)
        obj.fields.append((name, val))
    return obj


def parse_message(data: bytes) -> GBObject:
    """
    Parse a full GalacticBuf message (with 4-byte header) into a GBObject.
    """
    if len(data) < 4:
        raise ValueError("Buffer too small for header")

    b = Buffer(data)
    version = b.read_u8()
    if version != 0x01:
        raise ValueError("Unsupported protocol version")

    field_count = b.read_u8()
    total_len = b.read_u16()
    if total_len != len(data):
        raise ValueError("Total length mismatch")

    obj = GBObject()
    for _ in range(field_count):
        name_len = b.read_u8()
        if name_len == 0:
            raise ValueError("Field name length cannot be zero")
        if b.pos + name_len > len(data):
            raise ValueError("Unexpected EOF while reading field name")
        name = b.data[b.pos:b.pos + name_len].decode("utf-8")
        b.pos += name_len

        val = read_value(b)
        obj.fields.append((name, val))

    if b.pos != len(data):
        raise ValueError("Extra bytes after parsing message")

    return obj


# =========================
#   Small usage example
# =========================

if __name__ == "__main__":
    # Message: user_id=1001, name="Alice", scores=[100, 200, 300]
    msg = GBObject()
    msg.fields.append(("user_id", GBValue.make_int(1001)))
    msg.fields.append(("name", GBValue.make_string("Alice")))

    scores_vals = [
        GBValue.make_int(100),
        GBValue.make_int(200),
        GBValue.make_int(300),
    ]
    msg.fields.append(("scores", GBValue.make_list(GBValue.TYPE_INT, scores_vals)))

    encoded = serialize_message(msg)
    print("Encoded length:", len(encoded))
    print("Encoded hex:", " ".join(f"{b:02X}" for b in encoded))

    decoded = parse_message(encoded)
    print("Decoded fields:")
    for name, val in decoded.fields:
        if val.type == GBValue.TYPE_INT:
            print(name, "=", val.int_value)
        elif val.type == GBValue.TYPE_STRING:
            print(name, "=", val.string_value)
        elif val.type == GBValue.TYPE_LIST:
            print(
                name,
                "=",
                [e.int_value for e in val.list_value.elements]
                if val.list_value.element_type == GBValue.TYPE_INT
                else "...",
            )
