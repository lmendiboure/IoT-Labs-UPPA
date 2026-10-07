"""Small RFC 7252 subset used by Lab 2.

The lab needs only GET requests, Uri-Path options, CON/NON messages and
piggybacked ACK responses. The encoder/decoder below emits normal CoAP v1
packets so the exercise observes real CoAP message semantics without pulling
an additional framework into the teaching image.
"""
from __future__ import annotations

import os
import secrets
import struct

COAP_VERSION = 1
TYPE_NAMES = {0: "CON", 1: "NON", 2: "ACK", 3: "RST"}
CODE_NAMES = {0: "0.00 Empty", 1: "0.01 GET", 69: "2.05 Content"}


def _nibble(value: int) -> tuple[int, bytes]:
    if value < 13:
        return value, b""
    if value < 269:
        return 13, bytes([value - 13])
    if value < 65805:
        return 14, struct.pack("!H", value - 269)
    raise ValueError("CoAP option delta/length too large for this lab")


def _read_extended(n: int, data: bytes, pos: int) -> tuple[int, int]:
    if n < 13:
        return n, pos
    if n == 13:
        if pos >= len(data):
            raise ValueError("truncated CoAP option")
        return 13 + data[pos], pos + 1
    if n == 14:
        if pos + 2 > len(data):
            raise ValueError("truncated CoAP option")
        return 269 + int.from_bytes(data[pos:pos + 2], "big"), pos + 2
    raise ValueError("reserved CoAP option nibble")


def encode_option(delta: int, value: bytes) -> bytes:
    dn, de = _nibble(delta)
    ln, le = _nibble(len(value))
    return bytes([(dn << 4) | ln]) + de + le + value


def encode_message(msg_type: int, code: int, mid: int, token: bytes = b"",
                   options: list[tuple[int, bytes]] | None = None,
                   payload: bytes = b"") -> bytes:
    if not 0 <= msg_type <= 3:
        raise ValueError("invalid CoAP type")
    if len(token) > 8:
        raise ValueError("CoAP token too long")
    first = (COAP_VERSION << 6) | (msg_type << 4) | len(token)
    out = bytearray([first, code]) + bytearray(struct.pack("!H", mid)) + bytearray(token)
    previous = 0
    for number, value in sorted(options or [], key=lambda item: item[0]):
        if number < previous:
            raise ValueError("CoAP options must be ordered")
        out += encode_option(number - previous, value)
        previous = number
    if payload:
        out.append(0xFF)
        out += payload
    return bytes(out)


def encode_get(path: str, *, confirmable: bool, mid: int, token: bytes) -> bytes:
    options = []
    previous = 0
    for segment in [x for x in path.strip("/").split("/") if x]:
        number = 11  # Uri-Path
        options.append((number, segment.encode()))
        previous = number
    return encode_message(0 if confirmable else 1, 1, mid, token, options, b"")


def decode_message(data: bytes) -> dict:
    if len(data) < 4:
        raise ValueError("short CoAP datagram")
    first, code = data[0], data[1]
    version = first >> 6
    msg_type = (first >> 4) & 0x03
    tkl = first & 0x0F
    if version != 1 or tkl > 8 or len(data) < 4 + tkl:
        raise ValueError("invalid CoAP header")
    mid = int.from_bytes(data[2:4], "big")
    token = data[4:4 + tkl]
    pos = 4 + tkl
    number = 0
    options: list[tuple[int, bytes]] = []
    payload = b""
    while pos < len(data):
        if data[pos] == 0xFF:
            payload = data[pos + 1:]
            break
        b = data[pos]
        pos += 1
        delta, pos = _read_extended(b >> 4, data, pos)
        length, pos = _read_extended(b & 0x0F, data, pos)
        number += delta
        if pos + length > len(data):
            raise ValueError("truncated CoAP option value")
        value = data[pos:pos + length]
        pos += length
        options.append((number, value))
    path = "/" + "/".join(v.decode(errors="replace") for n, v in options if n == 11)
    return {
        "version": version,
        "type": msg_type,
        "type_name": TYPE_NAMES.get(msg_type, str(msg_type)),
        "code": code,
        "code_name": CODE_NAMES.get(code, f"{code >> 5}.{code & 0x1f:02d}"),
        "mid": mid,
        "token": token,
        "options": options,
        "path": path,
        "payload": payload,
    }


def describe(msg: dict) -> str:
    token = msg["token"].hex() or "-"
    return (f"{msg['type_name']} {msg['code_name']} "
            f"mid=0x{msg['mid']:04x} token={token} path={msg['path'] or '-'}")


def new_mid() -> int:
    return secrets.randbelow(65536)


def new_token() -> bytes:
    return secrets.token_bytes(4)
