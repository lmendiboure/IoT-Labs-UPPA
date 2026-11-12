"""Proof that broker ACL is an independent protection from the web route.

Publishes one synthetic record under the gateway account from the isolated OT workstation.
Checks actual delivery at the OT quality application rather than trusting PUBACK alone.
"""
import argparse
import json
import threading
import time
import urllib.request
import paho.mqtt.client as mqtt

TOPIC='quality/autoclave/AC-1/cure-records'

def record_seen(base,rid):
    try:
        with urllib.request.urlopen(base+'/api/status',timeout=4) as r:
            events=json.load(r)['events']
        return any(isinstance(e.get('payload'),dict) and
                   e['payload'].get('record_id')==rid for e in events)
    except Exception:
        return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--expect',choices=['allowed','blocked'],required=True)
    ap.add_argument('--quality-url',default='http://quality:8091')
    args=ap.parse_args()
    rid='CR-ACL-'+str(int(time.time()*1000)%100000000)
    connected=threading.Event()
    ack=threading.Event()
    result=[]
    def on_connect(c,u,flags,reason,properties):
        result.append(('CONNACK',str(reason)))
        if reason==0:connected.set()
    def on_publish(c,u,mid,reason,properties):
        result.append(('PUBACK',str(reason)))
        ack.set()
    c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                  client_id='acl-probe-'+str(int(time.time()*1000)%100000000),
                  protocol=mqtt.MQTTv5)
    c.username_pw_set('gateway','gateway-demo')
    c.on_connect=on_connect;c.on_publish=on_publish
    c.connect('broker',1883,25);c.loop_start()
    try:
        if not connected.wait(8):raise SystemExit('FAIL: gateway account could not CONNECT to broker')
        data={'record_id':rid,'result':'PASS','device_id':'AC-1',
              'batch':'ACL-PROBE','timestamp':'training'}
        info=c.publish(TOPIC,json.dumps(data),qos=1)
        ack.wait(7)
        print('MQTT evidence:',result,'publish_rc=',info.rc)
        seen=False
        for _ in range(12):
            seen=record_seen(args.quality_url,rid)
            if seen:break
            time.sleep(.5)
        should=args.expect=='allowed'
        if seen!=should:
            raise SystemExit(f'FAIL: expected delivered={should}, observed={seen} (ID {rid})')
        print('PASS',args.expect,'OT receipt=',seen,'record_id=',rid)
    finally:
        c.loop_stop();c.disconnect()

if __name__=='__main__':main()
