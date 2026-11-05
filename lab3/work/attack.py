"""Publish a synthetic measurement in this isolated teaching stack.

Never point this at infrastructure outside the classroom lab.
"""
import argparse
import json
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from mqtt_lab import connection_args, new_client, target

TEMP_TOPIC = 'plant/autoclave/AC-1/temperature'
CURE_TOPIC = 'quality/autoclave/AC-1/cure-records'

def main():
    p = connection_args(argparse.ArgumentParser(description='Lab-only MQTT measurement injection'))
    p.add_argument('--value', type=float, default=999.0)
    p.add_argument('--topic', default=None, help='override the default topic for this demonstration')
    p.add_argument('--record-id', help='instead publish a synthetic cure record, as in Lab 2')
    p.add_argument('--result', choices=('PASS', 'FAIL'), default='PASS', help='cure record outcome')
    p.add_argument('--seq', type=int, default=9001)
    args = p.parse_args()
    client = new_client('lab3-test-publisher', args)
    connected = threading.Event()
    completed = threading.Event()
    result = {'connect': None, 'publish': None}

    def on_connect(c, userdata, flags, reason_code, properties):
        result['connect'] = reason_code
        connected.set()

    def on_publish(c, userdata, mid, reason_code, properties):
        result['publish'] = reason_code
        completed.set()

    client.on_connect = on_connect
    client.on_publish = on_publish
    host, port = target(args)
    print(f'Connecting to {host}:{port} user={"anonymous" if args.anonymous else args.user}')
    try:
        client.connect(host, port, keepalive=15)
        client.loop_start()
        if not connected.wait(5):
            raise RuntimeError('No CONNACK received')
        print('CONNACK:', result['connect'])
        if result['connect'].is_failure:
            print('Connection denied; no PUBLISH was attempted')
            return 2
        if args.record_id:
            topic = args.topic or CURE_TOPIC
            payload_data = {
                'record_id': args.record_id,
                'batch': f"BATCH-{args.record_id.split('-')[-1]}",
                'completed_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                'recipe': 'CFRP-180C', 'max_air_c': 180.4,
                'min_pressure_bar': 6.96, 'result': args.result,
                'device_id': 'AC-1',
            }
        else:
            topic = args.topic or TEMP_TOPIC
            payload_data = {'device_id': 'AC-1', 'seq': args.seq,
                            'temperature_c': args.value,
                            'measured_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
        payload = json.dumps(payload_data, separators=(',', ':'))
        print('PUBLISH topic:', topic)
        print('PUBLISH payload:', payload)
        info = client.publish(topic, payload, qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f'Local publish failed: {info.rc}')
        if not completed.wait(6):
            print('No PUBACK received; inspect broker/relay logs, do not infer delivery')
            return 3
        print('PUBACK:', result['publish'])
        if result['publish'].is_failure:
            print('Broker reported publish failure')
            return 4
        print('Broker acknowledged this MQTT delivery; check the separate quality application output')
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print('Connection/protocol error:', exc)
        return 5
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == '__main__':
    raise SystemExit(main())
