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

def split_top_level_fields(s: str) -> List[str]:
    """
    Split the whole CLI string into top-level 'key=value' tokens,
    splitting on spaces that are not inside [] or {}.
    """
    fields = []
    current = []
    depth = 0  # nesting depth for [] and {}

    for ch in s:
        if ch in "[{":
            depth += 1
            current.append(ch)
        elif ch in "]}":
            depth -= 1
            current.append(ch)
        elif ch == " " and depth == 0:
            if current:
                fields.append("".join(current).strip())
                current = []
        else:
            current.append(ch)

    if current:
        fields.append("".join(current).strip())

    return fields


def split_top_level_items(s: str) -> List[str]:
    """
    Split a list or object inner content into items, separated by commas or spaces,
    but ignore separators inside nested [] or {}.
    """
    items = []
    current = []
    depth = 0

    for ch in s:
        if ch in "[{":
            depth += 1
            current.append(ch)
        elif ch in "]}":
            depth -= 1
            current.append(ch)
        elif (ch == "," or ch == " ") and depth == 0:
            if current:
                items.append("".join(current).strip())
                current = []
        else:
            current.append(ch)

    if current:
        items.append("".join(current).strip())

    # Remove empty items
    return [it for it in items if it]


def parse_scalar_value(value_str: str) -> GBValue:
    value_str = value_str.strip()
    # Try int
    try:
        v = int(value_str)
        return GBValue.make_int(v)
    except ValueError:
        pass

    # String (strip quotes if present)
    s = value_str
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1]
    return GBValue.make_string(s)


def parse_object_from_string(inner: str) -> GBObject:
    """
    Parse something like "id:1, price:100" into a GBObject.
    Values inside objects are treated as scalars (int or string).
    """
    obj = GBObject()
    parts = split_top_level_items(inner)
    for part in parts:
        if ":" not in part:
            continue
        name, val_str = part.split(":", 1)
        name = name.strip()
        val_str = val_str.strip()
        if not name:
            raise ValueError("Empty object field name")
        val = parse_scalar_value(val_str)
        obj.fields.append((name, val))
    return obj


def parse_value_from_string(value_str: str) -> GBValue:
    value_str = value_str.strip()

    # List: [ ... ]
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1].strip()
        if not inner:
            # empty list -> list of strings by default
            return GBValue.make_list(GBValue.TYPE_STRING, [])

        items = split_top_level_items(inner)

        # List of objects?  [{...} {...}] or [{...}, {...}]
        if all(it.startswith("{") and it.endswith("}") for it in items):
            objs: List[GBValue] = []
            for it in items:
                inner_obj = it[1:-1].strip()
                obj = parse_object_from_string(inner_obj)
                objs.append(GBValue.make_object(obj))
            return GBValue.make_list(GBValue.TYPE_OBJECT, objs)

        # Try list of ints
        all_int = True
        int_vals: List[int] = []
        for it in items:
            try:
                int_vals.append(int(it))
            except ValueError:
                all_int = False
                break

        if all_int:
            elems = [GBValue.make_int(v) for v in int_vals]
            return GBValue.make_list(GBValue.TYPE_INT, elems)

        # Otherwise list of strings
        str_elems: List[GBValue] = []
        for it in items:
            s = it
            if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
                s = s[1:-1]
            str_elems.append(GBValue.make_string(s))
        return GBValue.make_list(GBValue.TYPE_STRING, str_elems)

    # Scalar (int or string)
    return parse_scalar_value(value_str)


def parse_cli_args_to_object(argv: List[str]) -> GBObject:
    """
    Parse command line arguments into a GBObject.

    Examples that work:
      user_id=1001 name=Alice scores=[100,200,300]
      timestamp=1698765432 trades=[{id:1,price:100},{id:2,price:200}]
      timestamp=1698765432 trades=[{id:1, price:100} {id:2, price:200}]
    """
    cmdline = " ".join(argv).strip()
    obj = GBObject()

    if not cmdline:
        return obj

    tokens = split_top_level_fields(cmdline)

    for token in tokens:
        token = token.strip().rstrip(",")
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Invalid argument (expected key=value): {token!r}")

        name, value_str = token.split("=", 1)
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
    obj = parse_cli_args_to_object(sys.argv[1:])
    encoded = serialize_message(obj)
    # Write raw GalacticBuf bytes to stdout (no extra prints!)
    sys.stdout.buffer.write(encoded)
