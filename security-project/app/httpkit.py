"""Minimal HTTP/JSON utilities to avoid another web framework dependency."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    def send_json(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def send_html(self,body):
        data=body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def read_json(self,max_size=4096):
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:return None
        if size<=0 or size>max_size:return None
        try:return json.loads(self.rfile.read(size))
        except (ValueError,UnicodeDecodeError):return None
    def log_message(self,*args):
        return
