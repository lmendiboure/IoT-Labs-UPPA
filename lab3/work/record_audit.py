"""Teaching audit subscriber for Lab 3 D: compare conflicting cure-record claims.

It reports observations made at the subscriber. It cannot verify physical cure
cycles and does not alter or validate the main quality console.
"""
import argparse
import json
import threading
import time

from mqtt_lab import connection_args, new_client, target

CURE_TOPIC = 'quality/autoclave/AC-1/cure-records'


def classify(record, first_seen):
    """Classify this claim against the first claim received for its record ID.

    Return (label, differing_fields, previous_claim). The state is volatile.
    JSON object field order has no effect on a comparison.
    """
    rid = record['record_id']
    previous = first_seen.get(rid)
    if previous is None:
        first_seen[rid] = dict(record)
        return 'FIRST', [], None
    fields = sorted(
        key for key in previous.keys() | record.keys()
        if key not in previous or key not in record or previous[key] != record[key]
    )
    if fields:
        return 'CONFLICT', fields, previous
    return 'REPEAT', [], previous


def main():
    parser = connection_args(argparse.ArgumentParser(
        description='Compare cure-record claims received through MQTT'))
    parser.set_defaults(user='quality')
    args = parser.parse_args()
    if args.anonymous or args.user != 'quality' or not args.tls:
        parser.error('Use the quality account over TLS: python record_audit.py --tls')

    first_seen = {}
    subscribed = threading.Event()
    authorized = {'ok': False}
    client = new_client('lab3-record-audit', args)

    def on_connect(c, userdata, flags, reason_code, properties):
        print('CONNACK:', reason_code, flush=True)
        if reason_code.is_failure:
            subscribed.set()
        else:
            c.subscribe(CURE_TOPIC, qos=1)

    def on_subscribe(c, userdata, mid, reason_codes, properties):
        authorized['ok'] = bool(reason_codes) and not any(
            code.is_failure for code in reason_codes)
        if authorized['ok']:
            print('READY: auditing cure-record claims (CR-SIM records hidden)', flush=True)
        else:
            print('SUBACK refused:', reason_codes, flush=True)
        subscribed.set()

    def on_message(c, userdata, msg):
        try:
            record = json.loads(msg.payload)
        except (UnicodeDecodeError, ValueError):
            return
        if not isinstance(record, dict):
            return
        rid = record.get('record_id')
        if not isinstance(rid, str) or not rid.startswith('CR-') or rid.startswith('CR-SIM-'):
            return
        label, changes, previous = classify(record, first_seen)
        outcome = record.get('result')
        if label == 'CONFLICT':
            print(f'{label} {rid} previous_result={previous.get("result")} '
                  f'new_result={outcome} changed={",".join(changes)}', flush=True)
        else:
            print(f'{label} {rid} result={outcome}', flush=True)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    host, port = target(args)
    print(f'Connecting to {host}:{port}', flush=True)
    try:
        client.connect(host, port, keepalive=20)
        client.loop_start()
        if not subscribed.wait(8):
            print('No SUBACK: check broker and ACL before continuing', flush=True)
            return 2
        if not authorized['ok']:
            print('Cannot observe cure records: connection or subscription failed', flush=True)
            return 2
        while True:
            time.sleep(1)
    except (OSError, ValueError) as exc:
        print('Connection error:', exc, flush=True)
        return 3
    except KeyboardInterrupt:
        return 0
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == '__main__':
    raise SystemExit(main())
