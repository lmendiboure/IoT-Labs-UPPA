"""decode.py — the freezer probe's application payload, from the 'data' field of a ChirpStack event (exercise 3).

    python decode.py <base64>      decode one frame, for example: python decode.py EfiYHFcA
    python decode.py --test        check your decoder against a frame whose content is known

The application payload, from the probe's datasheet (6 bytes):

    byte   0            1-2                               3          4         5
           frame type   temperature, hundredths of °C,    humidity   battery   status
           (0x11)       signed, big-endian                %          %

Exercise 6 imports decode() from this file: keep its name and what it returns.
"""
import base64
import struct
import sys


def decode(data_b64):
    """Return the probe's values from the base64 text of the 'data' field."""
    raw = b""                       # TODO: the bytes hidden in the base64 text
    # TODO: unpack the 6-byte application payload with struct.unpack(FORMAT, raw).
    #   In a format, '>' means big-endian, 'B' one unsigned byte, 'b' one signed byte,
    #   'H' two bytes unsigned, 'h' two bytes signed. Which five letters describe this frame?
    kind, centi, rh, battery, status = 0, 0, 0, 0, 0
    return {"bytes": len(raw), "frame_type": kind, "temperature_c": centi / 100,
            "humidity_pct": rh, "battery_pct": battery, "status": status}


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        got = decode("EfiYHFcA")    # a frame sent by FRZ1-T1 on a cold morning
        want = {"bytes": 6, "frame_type": 0x11, "temperature_c": -18.96,
                "humidity_pct": 28, "battery_pct": 87, "status": 0}
        for key, value in want.items():
            print(f"{'ok ' if got.get(key) == value else 'NO '} {key}: {got.get(key)} (expected {value})")
    elif len(sys.argv) == 2:
        print(decode(sys.argv[1]))
    else:
        print(__doc__)
