"""IoT cyber teaching network: private demonstration credentials only."""
import json
import os
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

TEMP_TOPIC = 'plant/autoclave/AC-1/temperature'
RECORD_TOPIC = 'quality/autoclave/AC-1/cure-records'
MQTT_HOST = os.getenv('MQTT_HOST', 'broker')
PASSWORDS = {'sensor':'sensor-demo','quality':'quality-demo',
             'gateway':'gateway-demo','auditor':'auditor-demo'}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def client(role, on_connect=None, on_message=None):
    name = role + '-' + str(os.getpid()) + '-' + str(int(time.time()*1000)%100000)
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name, protocol=mqtt.MQTTv5)
    c.username_pw_set(role, PASSWORDS[role])
    if on_connect:
        c.on_connect = on_connect
    if on_message:
        c.on_message = on_message
    c.connect_async(MQTT_HOST, 1883, keepalive=25)
    c.loop_start()
    return c


def json_message(payload):
    try:
        data=json.loads(payload)
        return data if isinstance(data,dict) else None
    except (ValueError,UnicodeDecodeError,TypeError):
        return None


def record(record_id, result='PASS', source='AC-1'):
    return {'record_id':record_id,'device_id':source,'result':result,
            'timestamp':utc_now(),'batch':'DEMO-CYBER'}
