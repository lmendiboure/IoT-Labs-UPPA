"""decode.py — decode the 6-byte application payload of a freezer probe.

    python decode.py <base64>      decode one real ChirpStack `data` field
    python decode.py --test        check the decoder with a known frame

The payload format is:

    byte   0            1-2                               3          4         5
           frame type   temperature, hundredths of °C,    humidity   battery   status
           (0x11)       signed, big-endian                %          %

`bridge.py` imports `decode()` from this file: keep its name and return keys.
"""
import base64
import sys


def decode(data_b64):
    """Return the values encoded in a ChirpStack base64 `data` field."""
    # ChirpStack puts arbitrary binary bytes in JSON by encoding them as base64 text.
    # This first conversion is not part of the exercise: `raw` is now the six bytes above.
    raw = base64.b64decode(data_b64)
    if len(raw) != 6:
        raise ValueError(f"expected a 6-byte probe payload, got {len(raw)} bytes")

    # Python bytes can be indexed directly: raw[0] is byte 0 as an integer from 0 to 255.
    kind = raw[0]

    # TODO: decode bytes 1-2 as one *signed*, big-endian integer.
    # `int.from_bytes(two_bytes, byteorder="big", signed=True)` is the operation you need.
    centi = 0

    # TODO: bytes 3, 4 and 5 are one-byte unsigned values.
    rh = 0
    battery = 0
    status = -1

    return {
        "raw_hex": raw.hex(" "),
        "bytes": len(raw),
        "frame_type": kind,
        "temperature_c": centi / 100,
        "humidity_pct": rh,
        "battery_pct": battery,
        "status": status,
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        got = decode("EfiYHFcA")    # bytes: 11 f8 98 1c 57 00
        want = {
            "bytes": 6,
            "frame_type": 0x11,
            "temperature_c": -18.96,
            "humidity_pct": 28,
            "battery_pct": 87,
            "status": 0,
        }
        for key, value in want.items():
            print(f"{'ok ' if got.get(key) == value else 'NO '} {key}: {got.get(key)} (expected {value})")
    elif len(sys.argv) == 2:
        print(decode(sys.argv[1]))
    else:
        print(__doc__)
