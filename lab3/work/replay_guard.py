"""Optional Lab 3 D: a separate MQTT quality subscriber for duplicate detection.

Works only for the current process; not a durable audit log or source attestation.
"""
import argparse
import json
import time
import threading

from mqtt_lab import connection_args, new_client, target
from replay_guard_logic import first_occurrence

CURE_TOPIC = 'quality/autoclave/AC-1/cure-records'


def main():
    parser = connection_args(argparse.ArgumentParser(description='Optional cure-record replay guard'))
    parser.set_defaults(user='quality')
    args = parser.parse_args()
    if args.anonymous or args.user != 'quality':
        parser.error('Use the quality account: python replay_guard.py --tls')

    seen_ids = set()
    subscribed = threading.Event()
    subscription_ok = {'value': False}
    client = new_client('lab3-replay-guard', args)

    def on_connect(c, userdata, flags, reason_code, properties):
        print('CONNACK:', reason_code, flush=True)
        if reason_code.is_failure:
            subscribed.set()
            return
        c.subscribe(CURE_TOPIC, qos=1)

    def on_subscribe(c, userdata, mid, reason_codes, properties):
        if any(code.is_failure for code in reason_codes):
            print('SUBACK refused:', reason_codes, flush=True)
        else:
            subscription_ok['value'] = True
            print('READY: watching cure-record IDs (ignoring CR-SIM background records)', flush=True)
        subscribed.set()

    def on_message(c, userdata, msg):
        try:
            data = json.loads(msg.payload)
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(data, dict):
            return
        rid = data.get('record_id')
        if not isinstance(rid, str) or not rid.startswith('CR-') or rid.startswith('CR-SIM-'):
            return
        first = first_occurrence(rid, seen_ids)
        print(f'{"FIRST" if first else "DUPLICATE"} {rid} (MQTT PUBLISH received)', flush=True)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    host, port = target(args)
    print(f'Connecting to {host}:{port}', flush=True)
    try:
        client.connect(host, port, keepalive=20)
        client.loop_start()
        subscribed.wait(8)
        if not subscribed.is_set():
            raise RuntimeError('No SUBACK received (check broker and ACL)')
        if not subscription_ok['value']:
            print('Cannot observe cure records: broker denied connection/subscription', flush=True)
            return 2
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == '__main__':
    raise SystemExit(main())
