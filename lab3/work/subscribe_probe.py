"""Attempt a MQTT SUBSCRIBE; optionally observe delivered messages.

Important: Mosquitto's classic acl_file may grant SUBSCRIBE but withhold
matching PUBLISH deliveries. A successful SUBACK is not evidence of read access.
"""
import argparse
import threading
import time

from mqtt_lab import connection_args, new_client, target


def main():
    parser = connection_args(argparse.ArgumentParser())
    parser.add_argument('--topic', default='plant/autoclave/AC-1/#')
    parser.add_argument('--listen-seconds', type=float, default=0,
                        help='observe actual PUBLISH deliveries after the SUBACK')
    args = parser.parse_args()
    if args.listen_seconds < 0:
        parser.error('--listen-seconds must be non-negative')

    client = new_client('lab3-subscribe-probe', args)
    connected, subscribed = threading.Event(), threading.Event()
    result = {'connect': None, 'subscribe': None, 'denied': None, 'received': 0}

    def on_connect(c, userdata, flags, reason_code, properties):
        result['connect'] = reason_code
        connected.set()

    def on_subscribe(c, userdata, mid, reason_codes, properties):
        result['subscribe'] = [str(code) for code in reason_codes]
        result['denied'] = any(code.is_failure for code in reason_codes)
        subscribed.set()

    def on_message(c, userdata, message):
        result['received'] += 1
        print(f'RECEIVED {message.topic}: {message.payload.decode("utf-8", errors="replace")[:180]}',
              flush=True)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    host, port = target(args)
    try:
        client.connect(host, port, keepalive=15)
        client.loop_start()
        if not connected.wait(5):
            print('No CONNACK')
            return 3
        print('CONNACK:', result['connect'], flush=True)
        if result['connect'].is_failure:
            return 2
        rc, _ = client.subscribe(args.topic, qos=1)
        if rc != 0:
            print('Local SUBSCRIBE failed:', rc)
            return 3
        if not subscribed.wait(5):
            print('No SUBACK')
            return 3
        print('SUBACK:', result['subscribe'], flush=True)
        if args.listen_seconds:
            print(f'Observing delivered messages for {args.listen_seconds:g} seconds...', flush=True)
            time.sleep(args.listen_seconds)
            print(f'DELIVERED_COUNT: {result["received"]}', flush=True)
        # This is an MQTT SUBACK result only: 0 does NOT prove read access.
        return 4 if result['denied'] else 0
    except (OSError, ValueError) as exc:
        print('Connection error:', exc)
        return 5
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == '__main__':
    raise SystemExit(main())
