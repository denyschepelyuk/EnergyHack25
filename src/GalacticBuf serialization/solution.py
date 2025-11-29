from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import sys


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


# =========================
#   Serialization helpers
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
#   CLI parsing
# =========================

def parse_value_from_string(value_str: str) -> GBValue:
    value_str = value_str.strip()

    # List: [a,b,c]
    if value_str.startswith('[') and value_str.endswith(']'):
        inner = value_str[1:-1].strip()
        if not inner:
            # empty list -> default to list-of-strings
            return GBValue.make_list(GBValue.TYPE_STRING, [])

        parts = [p.strip() for p in inner.split(',')]

        # Try int list
        all_int = True
        int_vals = []
        for p in parts:
            try:
                int_vals.append(int(p))
            except ValueError:
                all_int = False
                break

        if all_int:
            elems = [GBValue.make_int(v) for v in int_vals]
            return GBValue.make_list(GBValue.TYPE_INT, elems)

        # Otherwise treat as list of strings (optionally strip quotes)
        str_elems = []
        for p in parts:
            if len(p) >= 2 and ((p[0] == '"' and p[-1] == '"') or (p[0] == "'" and p[-1] == "'")):
                p = p[1:-1]
            str_elems.append(GBValue.make_string(p))
        return GBValue.make_list(GBValue.TYPE_STRING, str_elems)

    # Scalar: try int first
    try:
        v = int(value_str)
        return GBValue.make_int(v)
    except ValueError:
        pass

    # Scalar string (strip optional quotes)
    s = value_str
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1]
    return GBValue.make_string(s)


def parse_cli_args_to_object(argv: List[str]) -> GBObject:
    """
    Expect arguments like:
      user_id=1001 name=Alice scores=[100,200,300]
    Each arg is one field (no commas required).
    """
    obj = GBObject()

    for arg in argv:
        arg = arg.strip().rstrip(',')  # allow trailing comma
        if not arg:
            continue
        if '=' not in arg:
            raise ValueError(f"Invalid argument (expected key=value): {arg!r}")

        name, value_str = arg.split('=', 1)
        name = name.strip()
        value_str = value_str.strip()

        if not name:
            raise ValueError("Empty field name")

        val = parse_value_from_string(value_str)
        obj.fields.append((name, val))

    return obj


# =========================
#   Main
# =========================

if __name__ == "__main__":
    # Build GBObject from CLI args
    obj = parse_cli_args_to_object(sys.argv[1:])

    # Serialize and write **raw bytes** to stdout
    encoded = serialize_message(obj)
    sys.stdout.buffer.write(encoded)
