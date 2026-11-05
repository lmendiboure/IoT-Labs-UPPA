"""Non-regression check: can quality receive both AC-1 business streams?

This checks operational delivery under the selected MQTT configuration.
It is not a cryptographic proof of physical sensor provenance.
"""
import argparse
import json
import threading

from mqtt_lab import connection_args, new_client, target
from quality_board_state import TEMPERATURE_TOPIC, CURE_TOPIC


def main():
    p = connection_args(argparse.ArgumentParser(description='Lab 3 quality-service regression'))
    p.set_defaults(user='quality')
    p.add_argument('--seconds', type=float, default=20)
    args = p.parse_args()
    if args.anonymous or args.user != 'quality':
        p.error('This check uses the quality account')
    connected = threading.Event()
    data_seen = threading.Event()
    result = {'connack': None, 'temperature': None, 'cure': None,
              'suback_failure': False}
    client = new_client('lab3-service-check', args)

    def on_connect(c, userdata, flags, reason_code, properties):
        result['connack'] = reason_code
        print('CONNACK:', reason_code, flush=True)
        if not reason_code.is_failure:
            c.subscribe([(TEMPERATURE_TOPIC, 1), (CURE_TOPIC, 1)])
        connected.set()

    def on_subscribe(c, userdata, mid, reason_codes, properties):
        if any(code.is_failure for code in reason_codes):
            result['suback_failure'] = True
            print('FAIL: subscription not authorized:', reason_codes, flush=True)
            data_seen.set()
        else:
            print('SUBACK:', reason_codes, flush=True)

    def on_message(c, userdata, msg):
        try:
            data = json.loads(msg.payload)
            if not isinstance(data, dict):
                return
            if msg.topic == TEMPERATURE_TOPIC and data.get('device_id') == 'AC-1' and type(data.get('seq')) is int:
                result['temperature'] = data
                print('RECEIVED temperature:', data.get('temperature_c'), 'seq:', data['seq'], flush=True)
            elif msg.topic == CURE_TOPIC and data.get('device_id') == 'AC-1' and str(data.get('record_id', '')).startswith('CR-SIM-'):
                result['cure'] = data
                print('RECEIVED cure record:', data['record_id'], data.get('result'), flush=True)
            if result['temperature'] and result['cure']:
                data_seen.set()
        except (ValueError, TypeError, AttributeError):
            print('Malformed application payload:', msg.payload[:100], flush=True)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    host, port = target(args)
    print(f'Quality regression over {"verified TLS" if args.tls else "plaintext"} to {host}:{port}')
    try:
        client.connect(host, port, keepalive=15)
        client.loop_start()
        if not connected.wait(6) or result['connack'].is_failure:
            print('FAIL: quality account cannot connect')
            return 2
        data_seen.wait(args.seconds)
        if result['suback_failure']:
            return 3
        if result['temperature'] and result['cure']:
            print('PASS: quality received a temperature and a new synthetic cure record')
            print('Scope: application reception only, not proof of physical measurement authenticity')
            return 0
        print('FAIL: incomplete quality service: temperature=', bool(result['temperature']),
              'cure=', bool(result['cure']))
        print('Host diagnosis: docker compose logs --tail=40 sensor broker')
        return 4
    except (OSError, ValueError) as exc:
        print('FAIL: connection or TLS verification:', exc)
        return 5
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == '__main__':
    raise SystemExit(main())
