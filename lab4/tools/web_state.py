"""Tiny read-only dashboard/health server, with no third-party web framework."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from urllib.parse import urlsplit, parse_qs


def run_server(port, title, get_state, ready):
    html = Path("/lab/dashboard.html").read_text(encoding="utf-8").replace("__TITLE__", title)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return  # Avoid overwhelming the container logs with UI polling.

        def write(self, payload, status=200, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            u = urlsplit(self.path)
            if u.path == "/health":
                is_ready = ready()
                value = json.dumps({"ready": is_ready}).encode()
                return self.write(value, 200 if is_ready else 503)
            if u.path == "/api/state":
                run = parse_qs(u.query).get("run", [None])[0]
                return self.write(json.dumps(get_state(run)).encode())
            if u.path == "/":
                return self.write(html.encode(), content_type="text/html; charset=utf-8")
            return self.write(b'{"error":"not found"}', 404)

    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
