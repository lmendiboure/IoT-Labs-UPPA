"""Quality subscriber and small live dashboard for the isolated Lab 3.

It displays what an MQTT consumer actually received. It is not a digital twin,
industrial safety monitor or independent authentication of a physical sensor.
"""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mqtt_lab import connection_args, new_client, target
from quality_board_state import QualityBoard, TEMPERATURE_TOPIC, CURE_TOPIC
from validate_student import assess

BOARD_PATH = os.path.join(os.path.dirname(__file__), 'quality_dashboard.html')


def serve_board(board, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split('?')[0] == '/api/status':
                body = json.dumps(board.snapshot()).encode('utf-8')
                mime = 'application/json; charset=utf-8'
            elif self.path.split('?')[0] in ('/', '/index.html'):
                with open(BOARD_PATH, 'rb') as fh:
                    body = fh.read()
                mime = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            return

    http = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    return http


def main():
    p = connection_args(argparse.ArgumentParser(description='Lab 3 quality application + dashboard'))
    p.set_defaults(user='quality')
    p.add_argument('--validate', action='store_true', help='use student temperature validation')
    p.add_argument('--board-port', type=int, default=8081)
    p.add_argument('--no-board', action='store_true', help='terminal-only mode')
    args = p.parse_args()
    board = QualityBoard(validate=args.validate)
    http = None
    if not args.no_board:
        try:
            http = serve_board(board, args.board_port)
            print(f'Quality board: http://localhost:{args.board_port} (forward port on VM)', flush=True)
        except OSError as exc:
            raise SystemExit(f'Port {args.board_port} unavailable. Stop older quality_monitor.py: {exc}')

    ready = threading.Event()
    c = new_client('quality-monitor', args)

    def on_connect(client, user_data, flags, reason_code, properties):
        print('CONNACK:', reason_code, flush=True)
        accepted = not reason_code.is_failure
        board.connection(accepted, f'MQTT connection: {reason_code}')
        if accepted:
            for topic in (TEMPERATURE_TOPIC, CURE_TOPIC):
                client.subscribe(topic, qos=1)
        ready.set()

    def on_disconnect(client, user_data, flags, reason_code, properties):
        board.connection(False, f'MQTT disconnected: {reason_code}')
        print('MQTT disconnected:', reason_code, flush=True)

    def on_message(client, user_data, msg):
        item = board.receive(msg.topic, msg.payload, validator=assess)
        if item:
            print(item['verdict'], item['kind'], item['summary'], flush=True)

    c.on_connect, c.on_disconnect, c.on_message = on_connect, on_disconnect, on_message
    host, port = target(args)
    print(f'Quality consumer on {host}:{port}; subscriptions: temperature and cure records', flush=True)
    try:
        c.connect(host, port, keepalive=20)
        c.loop_start()
        ready.wait(7)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        c.disconnect()
        c.loop_stop()
        if http:
            http.shutdown()
            http.server_close()


if __name__ == '__main__':
    main()
