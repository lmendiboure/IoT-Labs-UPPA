"""Synthetic sensor. It does not drive physical equipment."""
import json
import time
import os
from shared import TEMP_TOPIC, RECORD_TOPIC, client, record, utc_now


def main():
    c=client('sensor')
    seq=0
    period=max(1.0,min(8.0,float(os.getenv('SENSOR_PERIOD','2'))))
    site=os.getenv('SENSOR_SITE_TAG','TARNOS')[:32]
    try:
        while True:
            seq+=1
            temp=178 + (seq%9)*0.7
            data={'device_id':'AC-1','seq':seq,'temperature':round(temp,1),'timestamp':utc_now(),'site':site}
            c.publish(TEMP_TOPIC,json.dumps(data),qos=1)
            if seq%5==0:
                c.publish(RECORD_TOPIC,json.dumps({**record(f'CR-SIM-{seq//5:05d}'),'site':site}),qos=1)
            time.sleep(period)
    finally:
        c.loop_stop(); c.disconnect()

if __name__=='__main__':main()
