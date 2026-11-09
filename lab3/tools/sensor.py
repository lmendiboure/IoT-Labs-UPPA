"""AC-1 simulated producer for the isolated teaching stack.

Connection details come from sensor/sensor.env via Compose. The students migrate
this producer from the teaching MQTT relay to the TLS listener without changing
its application payload or topic names. MQTT/TLS secures transport only; this is
not a source of real industrial measurements or cryptographic sensor attestation.
"""
import json
import os
import ssl
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

TOPIC = 'plant/autoclave/AC-1/temperature'
CURE_TOPIC = 'quality/autoclave/AC-1/cure-records'
PUBLIC_TOPIC = 'public/site/status'
TRANSPORT = os.getenv('MQTT_TRANSPORT', 'plaintext').strip().lower()
HOST = os.getenv('MQTT_HOST', 'relay').strip()
PORT = int(os.getenv('MQTT_PORT', '1884'))
CA_PATH = os.getenv('MQTT_CA_PATH', '/lab/ca.crt')


def build_client(connected):
    if TRANSPORT not in ('plaintext', 'tls'):
        raise ValueError('MQTT_TRANSPORT must be plaintext or tls')
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id='ac1-sensor', protocol=mqtt.MQTTv311)
    c.username_pw_set('ac1', 'ac1-demo')
    if TRANSPORT == 'tls':
        c.tls_set(ca_certs=CA_PATH, cert_reqs=ssl.CERT_REQUIRED,
                  tls_version=ssl.PROTOCOL_TLS_CLIENT)
        # Paho checks the broker hostname. Do not disable verification.

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            connected.clear()
            print('AC-1 CONNACK denied:', reason_code, flush=True)
        else:
            connected.set()
            print(f'AC-1 CONNECTED transport={TRANSPORT} to {HOST}:{PORT}', flush=True)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        connected.clear()
        print('AC-1 connection lost:', reason_code, flush=True)

    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.reconnect_delay_set(min_delay=1, max_delay=6)
    return c


def main():
    connected = threading.Event()
    client = build_client(connected)
    print(f'AC-1 target: {TRANSPORT} {HOST}:{PORT}', flush=True)
    # Start the network loop even if the initial connection cannot succeed.
    # On a later broker/profile restart, Paho will reconnect automatically.
    while True:
        try:
            client.connect(HOST, PORT, keepalive=20)
            break
        except (OSError, TimeoutError) as exc:
            print('AC-1 waiting for reachable broker:', exc, flush=True)
            time.sleep(3)
    client.loop_start()
    seq = 0
    try:
        while True:
            if not connected.wait(timeout=5):
                print('AC-1 OFFLINE — no new measurement sent', flush=True)
                continue
            seq += 1
            value = round(179.4 + ((seq % 7) - 3) * 0.2, 1)
            payload = json.dumps({
                'device_id': 'AC-1', 'seq': seq, 'temperature_c': value,
                'measured_at': datetime.now(timezone.utc).isoformat(timespec='seconds')
            }, separators=(',', ':'))
            info = client.publish(TOPIC, payload, qos=1)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                try:
                    info.wait_for_publish(timeout=3)
                    if info.is_published():
                        print(f'AC-1 published seq={seq} temperature_c={value} via {TRANSPORT}', flush=True)
                    else:
                        print(f'AC-1 delivery ACK pending seq={seq}', flush=True)
                except RuntimeError as exc:
                    print('AC-1 publish interrupted:', exc, flush=True)
            else:
                print('AC-1 local publish failed:', info.rc, flush=True)
            if seq % 4 == 1 and connected.is_set():
                # Accelerated teaching timeline: this represents an already-completed
                # synthetic cure cycle, not an actual 12-second industrial cure.
                rid = f'CR-SIM-{(seq - 1)//4 + 1:03d}'
                record = {
                    'record_id': rid, 'batch': f'BATCH-{(seq - 1)//4 + 1:03d}',
                    'completed_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                    'recipe': 'CFRP-180C', 'max_air_c': 180.4,
                    'min_pressure_bar': 6.96, 'result': 'PASS',
                    'device_id': 'AC-1'
                }
                client.publish(CURE_TOPIC, json.dumps(record, separators=(',', ':')), qos=1)
                print(f'AC-1 published completed cure record {rid} via {TRANSPORT}', flush=True)
                # One minimal, non-sensitive public event so learners can test that
                # permitted public subscriptions receive actual data, not only SUBACK.
                public_status = {'site': 'Adour Composites', 'line': 'AC-1',
                                 'status': 'RUNNING'}
                client.publish(PUBLIC_TOPIC, json.dumps(public_status, separators=(',', ':')), qos=1)
            time.sleep(3)
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == '__main__':
    main()
