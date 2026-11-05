"""Attempt one MQTT SUBSCRIBE and report the MQTT v5 SUBACK reason code."""
import argparse
import threading

from mqtt_lab import connection_args, new_client, target


def main():
    p = connection_args(argparse.ArgumentParser())
    p.add_argument('--topic', default='plant/autoclave/AC-1/#')
    args = p.parse_args()
    c = new_client('lab3-subscribe-probe', args)
    connected, subscribed = threading.Event(), threading.Event()
    result = {'connect': None, 'subscribe': None}
    def on_connect(client, user_data, flags, reason_code, properties):
        result['connect'] = reason_code
        connected.set()
    def on_subscribe(client, user_data, mid, reason_codes, properties):
        result['subscribe'] = [str(r) for r in reason_codes]
        subscribed.set()
    c.on_connect, c.on_subscribe = on_connect, on_subscribe
    h,pn = target(args)
    try:
        c.connect(h, pn, 15)
        c.loop_start()
        if not connected.wait(5):
            print('No CONNACK'); return 3
        print('CONNACK:', result['connect'])
        if result['connect'].is_failure:
            return 2
        c.subscribe(args.topic, qos=1)
        if not subscribed.wait(5):
            print('No SUBACK'); return 3
        print('SUBACK:', result['subscribe'])
        return 0 if all('Not authorized' not in s and 'Unspecified error' not in s for s in result['subscribe']) else 4
    except OSError as exc:
        print('Connection error:', exc)
        return 5
    finally:
        c.disconnect()
        c.loop_stop()

if __name__ == '__main__':
    raise SystemExit(main())
