"""The relay: a see-through MQTT proxy with a web viewer.

Every client of the lab connects here (port 1884) instead of to the broker
(port 1883). The relay forwards every byte to the broker and back, and on the
way decodes each MQTT packet: who sent it, its type, QoS, flags, topic, sizes.
The viewer (port 8080) shows them live.

It can also "freeze" a connection: from then on it forwards nothing, in either
direction, and closes nothing - exactly what a radio link that silently dies
looks like from both ends.

Plain Python, no dependency: read it, it is part of the lab.
"""
import asyncio
import collections
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BROKER_HOST = os.getenv("BROKER_HOST", "broker")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))
LISTEN_PORT = int(os.getenv("RELAY_PORT", "1884"))
WEB_PORT = int(os.getenv("VIEWER_PORT", "8080"))
HERE = os.path.dirname(os.path.abspath(__file__))

TYPES = {1: "CONNECT", 2: "CONNACK", 3: "PUBLISH", 4: "PUBACK", 5: "PUBREC", 6: "PUBREL",
         7: "PUBCOMP", 8: "SUBSCRIBE", 9: "SUBACK", 10: "UNSUBSCRIBE", 11: "UNSUBACK",
         12: "PINGREQ", 13: "PINGRESP", 14: "DISCONNECT", 15: "AUTH"}

lock = threading.Lock()
packets = collections.deque(maxlen=50000)     # every packet seen, newest last
connections = collections.OrderedDict()        # id -> Conn
seq = 0


def now():
    return time.time()


# ---------------------------------------------------------------- decoding
class Reader:
    def __init__(self, data):
        self.b, self.i = data, 0

    def byte(self):
        v = self.b[self.i]
        self.i += 1
        return v

    def u16(self):
        v = int.from_bytes(self.b[self.i:self.i + 2], "big")
        self.i += 2
        return v

    def varint(self):
        mult, v = 1, 0
        while True:
            d = self.byte()
            v += (d & 0x7F) * mult
            if not d & 0x80:
                return v
            mult *= 128

    def blob(self):
        n = self.u16()
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def text(self):
        return self.blob().decode("utf-8", "replace")

    def skip_props(self, level):
        if level == 5:
            n = self.varint()
            self.i += n

    def rest(self):
        return self.b[self.i:]


def preview(payload, limit=160):
    try:
        s = payload.decode("utf-8")
        if all(c.isprintable() or c in "\r\n\t" for c in s):
            return s if len(s) <= limit else s[:limit] + "…"
    except UnicodeDecodeError:
        pass
    h = payload.hex(" ")
    return "hex: " + (h if len(h) <= limit else h[:limit] + "…")


def split_packet(buf):
    """-> (packet bytes, rest) or (None, buf) when the packet is not complete."""
    if len(buf) < 2:
        return None, buf
    mult, length, i = 1, 0, 1
    while True:
        if i >= len(buf):
            return None, buf
        d = buf[i]
        length += (d & 0x7F) * mult
        i += 1
        if not d & 0x80:
            break
        mult *= 128
        if i > 4:
            raise ValueError("malformed remaining length")
    total = i + length
    if len(buf) < total:
        return None, buf
    return buf[:total], buf[total:]


def decode(pkt, conn):
    """What a viewer needs to know about one packet."""
    b0 = pkt[0]
    ptype, flags = b0 >> 4, b0 & 0x0F
    r = Reader(pkt)
    r.i = 1
    r.varint()
    header = r.i
    info = {"type": TYPES.get(ptype, f"?{ptype}"), "size": len(pkt), "header": header,
            "qos": None, "retain": None, "dup": None, "topic": None, "payload_size": None,
            "payload": None, "packet_id": None, "detail": ""}
    level = conn.level
    try:
        if ptype == 1:                                           # CONNECT
            name = r.text()
            level = r.byte()
            conn.level = level
            f = r.byte()
            conn.keepalive = r.u16()
            r.skip_props(level)
            conn.client_id = r.text() or "(no client id)"
            conn.clean = bool(f & 0x02)
            if f & 0x04:
                if level == 5:
                    r.skip_props(5)
                conn.will = {"topic": r.text(), "payload": preview(r.blob(), 60),
                             "qos": (f >> 3) & 3, "retain": bool(f & 0x20)}
            conn.username = r.text() if f & 0x80 else None
            info["detail"] = f"{name} v{ {3: '3.1', 4: '3.1.1', 5: '5'}.get(level, level) }"
        elif ptype == 2:                                         # CONNACK
            sp, rc = r.byte(), r.byte()
            info["detail"] = "connection accepted" if rc == 0 else f"connection refused (code {rc})"
            conn.accepted = rc == 0
        elif ptype == 3:                                         # PUBLISH
            qos = (flags >> 1) & 3
            info.update(qos=qos, retain=bool(flags & 1), dup=bool(flags & 8))
            info["topic"] = r.text()
            if qos:
                info["packet_id"] = r.u16()
            r.skip_props(level)
            payload = r.rest()
            info["payload_size"] = len(payload)
            info["payload"] = preview(payload, 4096)
        elif ptype in (4, 5, 6, 7, 11):                          # acks carrying a packet id
            info["packet_id"] = r.u16()
        elif ptype == 8:                                         # SUBSCRIBE
            info["packet_id"] = r.u16()
            r.skip_props(level)
            subs = []
            while r.i < len(pkt):
                t = r.text()
                opt = r.byte()
                subs.append(t)
            info["topic"] = ", ".join(subs)
        elif ptype == 9:                                         # SUBACK
            info["packet_id"] = r.u16()
            r.skip_props(level)
            info["detail"] = "subscription accepted"
        elif ptype == 10:                                        # UNSUBSCRIBE
            info["packet_id"] = r.u16()
            r.skip_props(level)
            subs = []
            while r.i < len(pkt):
                subs.append(r.text())
            info["topic"] = ", ".join(subs)
    except (IndexError, ValueError) as e:
        info["detail"] = f"could not decode: {e}"
    return info


# ---------------------------------------------------------------- connections
class Conn:
    counter = 0

    def __init__(self, peer):
        Conn.counter += 1
        self.id = Conn.counter
        self.peer = peer
        self.client_id = None
        self.level = 4
        self.keepalive = None
        self.clean = None
        self.will = None
        self.username = None
        self.accepted = None
        self.opened = now()
        self.closed = None
        self.end = None                # clean / abrupt / closed by broker / frozen ...
        self.frozen_at = None
        self.last_from_client = None
        self.bytes_up = self.bytes_down = 0
        self.packets_up = self.packets_down = 0

    def view(self):
        return {"id": self.id, "client_id": self.client_id, "peer": self.peer,
                "keepalive": self.keepalive, "clean": self.clean, "will": self.will,
                "opened": self.opened, "closed": self.closed, "end": self.end,
                "frozen_at": self.frozen_at, "bytes_up": self.bytes_up,
                "bytes_down": self.bytes_down, "packets_up": self.packets_up,
                "packets_down": self.packets_down}


def record(conn, direction, info):
    global seq
    with lock:
        seq += 1
        info.update(seq=seq, t=now(), dir=direction, conn=conn.id, client=conn.client_id)
        packets.append(info)


async def pump(conn, reader, writer, direction, other_writer):
    buf = b""
    while True:
        try:
            data = await reader.read(65536)
        except (ConnectionError, OSError):
            data = b""
        if not data:
            return
        buf += data
        while True:
            try:
                pkt, buf = split_packet(buf)
            except ValueError:
                return
            if pkt is None:
                break
            info = decode(pkt, conn)
            if direction == "up":
                conn.bytes_up += len(pkt)
                conn.packets_up += 1
                conn.last_from_client = info["type"]
            else:
                conn.bytes_down += len(pkt)
                conn.packets_down += 1
            if conn.frozen_at is not None:
                info["detail"] = ("dropped: link frozen. " + info["detail"]).strip()
                info["dropped"] = True
            record(conn, direction, info)
            if conn.frozen_at is None:
                writer.write(pkt)
        if conn.frozen_at is None:
            try:
                await writer.drain()
            except (ConnectionError, OSError):
                return


async def handle(client_reader, client_writer):
    peer = client_writer.get_extra_info("peername")
    conn = Conn(f"{peer[0]}:{peer[1]}" if peer else "?")
    with lock:
        connections[conn.id] = conn
        while len(connections) > 500:
            connections.popitem(last=False)
    try:
        broker_reader, broker_writer = await asyncio.open_connection(BROKER_HOST, BROKER_PORT)
    except OSError:
        conn.end, conn.closed = "broker unreachable", now()
        client_writer.close()
        return
    up = asyncio.create_task(pump(conn, client_reader, broker_writer, "up", client_writer))
    down = asyncio.create_task(pump(conn, broker_reader, client_writer, "down", broker_writer))
    done, _ = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
    if conn.frozen_at is not None and up in done and down not in done:
        # the client gave up on a frozen link; the broker has not noticed anything:
        # keep its side open until its keepalive timer runs out, as on a dead radio link
        await down
        conn.end = f"frozen: broker gave up after {now() - conn.frozen_at:.0f} s"
    elif up in done:
        conn.end = conn.end or ("clean (DISCONNECT)" if conn.last_from_client == "DISCONNECT"
                                else "abrupt (no DISCONNECT)")
    else:
        if conn.frozen_at is not None:
            conn.end = f"frozen: broker gave up after {now() - conn.frozen_at:.0f} s"
        else:
            conn.end = conn.end or "closed by the broker"
    conn.closed = now()
    for w in (client_writer, broker_writer):
        try:
            w.close()
        except Exception:
            pass
    for t in (up, down):
        t.cancel()


# ---------------------------------------------------------------- web viewer
def topic_stats(window):
    """Per topic, over the last `window` seconds: what clients publish to the broker."""
    since = now() - window
    stats = {}
    with lock:
        items = [p for p in packets if p["t"] >= since and p["type"] == "PUBLISH" and p["dir"] == "up"]
    for p in items:
        s = stats.setdefault(p["topic"], {"topic": p["topic"], "messages": 0, "payload_bytes": 0,
                                          "packet_bytes": 0, "publishers": set(), "qos": set(),
                                          "retained": 0, "first": p["t"], "last": p["t"]})
        s["messages"] += 1
        s["payload_bytes"] += p["payload_size"] or 0
        s["packet_bytes"] += p["size"]
        s["publishers"].add(p["client"] or "?")
        s["qos"].add(p["qos"])
        s["retained"] += 1 if p["retain"] else 0
        s["last"] = p["t"]
    out = []
    for s in stats.values():
        n = s["messages"]
        span = s["last"] - s["first"]
        out.append({"topic": s["topic"], "messages": n,
                    "avg_payload": round(s["payload_bytes"] / n, 1),
                    "avg_packet": round(s["packet_bytes"] / n, 1),
                    "period_s": round(span / (n - 1), 1) if n > 1 else None,
                    "publishers": sorted(s["publishers"]), "qos": sorted(s["qos"]),
                    "retained": s["retained"]})
    return sorted(out, key=lambda s: s["topic"])


def totals(window):
    since = now() - window
    with lock:
        items = [p for p in packets if p["t"] >= since]
    up = sum(p["size"] for p in items if p["dir"] == "up")
    down = sum(p["size"] for p in items if p["dir"] == "down")
    pubs = [p for p in items if p["dir"] == "up" and p["type"] == "PUBLISH"]
    return {"window_s": window, "packets": len(items), "bytes_up": up, "bytes_down": down,
            "publish_up": len(pubs), "publish_up_bytes": sum(p["size"] for p in pubs)}


class Web(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "viewer.html"), "rb") as f:
                return self.send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/packets":
            since = int(q.get("since", 0))
            limit = int(q.get("limit", 1000))
            with lock:
                items = [p for p in packets if p["seq"] > since]
            return self.send(200, items[-limit:])
        if u.path == "/api/connections":
            with lock:
                items = [c.view() for c in connections.values()]
            return self.send(200, items)
        if u.path == "/api/topics":
            return self.send(200, topic_stats(float(q.get("window", 300))))
        if u.path == "/api/totals":
            return self.send(200, totals(float(q.get("window", 60))))
        return self.send(404, {"error": "unknown path"})

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/api/freeze":
            with lock:
                found = [c for c in connections.values() if c.closed is None and
                         (str(c.id) == q.get("id") or (q.get("client") and c.client_id == q.get("client")))]
            for c in found:
                c.frozen_at = c.frozen_at or now()
            if not found:
                return self.send(404, {"error": "no open connection with that id or client id"})
            return self.send(200, {"frozen": [c.id for c in found]})
        return self.send(404, {"error": "unknown path"})


def main():
    web = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Web)
    threading.Thread(target=web.serve_forever, daemon=True).start()
    print(f"relay: MQTT on :{LISTEN_PORT} -> {BROKER_HOST}:{BROKER_PORT}, viewer on :{WEB_PORT}", flush=True)

    async def serve():
        server = await asyncio.start_server(handle, "0.0.0.0", LISTEN_PORT)
        async with server:
            await server.serve_forever()

    asyncio.run(serve())


if __name__ == "__main__":
    main()
