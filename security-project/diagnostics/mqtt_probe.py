"""Authorized read-only audit of the broker from the OT workstation."""
import argparse, json, time
import paho.mqtt.client as mqtt
from argparse import Namespace

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=10)
    args=parser.parse_args()
    def on_connect(c,u,flags,rc,props):
        print('CONNACK',rc,flush=True)
        if rc==0:c.subscribe('quality/autoclave/AC-1/cure-records',qos=1)
    def on_message(c,u,msg):print('RECEIVED',msg.topic,msg.payload.decode('utf-8','replace'),flush=True)
    c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='auditor-'+str(int(time.time())%100000),protocol=mqtt.MQTTv5)
    c.username_pw_set('auditor','auditor-demo')
    c.on_connect=on_connect;c.on_message=on_message
    c.connect('broker',1883,keepalive=20)
    c.loop_start()
    try:time.sleep(max(1,min(args.seconds,60)))
    finally:c.loop_stop();c.disconnect()

if __name__=='__main__': main()
