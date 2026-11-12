"""IT maintenance gateway for the isolated cyber training environment."""
import json
import time
from pathlib import Path
from threading import Lock
from http.server import ThreadingHTTPServer
from shared import client, TEMP_TOPIC, RECORD_TOPIC, record
from state import State
from httpkit import Handler
from policy import build_test_record,may_publish_cure_record,may_read_config

STATE=State()
CLIENT=None
GUARD=Lock()
LAST_REQUEST=0.0
HTML=Path('/app/dashboard.html').read_text(encoding='utf-8')

def mode():
    try:
        s=Path('/control/mode.txt').read_text().strip()
        return s if s in ('vulnerable','hardened') else 'hardened'
    except OSError: return 'hardened'

def on_connect(client,userdata,flags,reason_code,properties):
    if reason_code==0:
        client.subscribe([(TEMP_TOPIC,1),(RECORD_TOPIC,1)])

def on_message(client,userdata,message):
    STATE.ingest(message.topic,message.payload)

class App(Handler):
    def do_GET(self):
        if self.path=='/':return self.send_html(HTML)
        if self.path in ('/health','/api/health'):return self.send_json({'status':'ok','mode':mode()})
        if self.path=='/api/status':return self.send_json(STATE.snapshot())
        if self.path=='/openapi.json':
            return self.send_json({'openapi':'3.0.0','info':{'title':'AC-1 IT Maintenance API','version':'1.0'},
                'paths':{'/api/maintenance/test-record':{'post':{'summary':'Test publication to OT quality stream',
                'requestBody':{'required':True},'responses':{'202':{'description':'Queued'},'403':{'description':'Forbidden'}}}},
                '/api/config':{'get':{'summary':'Configuration summary'}}}})
        if self.path=='/api/config':
            if not may_read_config(mode(),None,None):return self.send_json({'error':'forbidden'},403)
            return self.send_json({'mqtt_host':'broker','mqtt_port':1883,
                'username':'gateway','password':'gateway-demo','scope':'demo-only'})
        return self.send_json({'error':'not found'},404)
    def do_POST(self):
        global LAST_REQUEST
        if self.path!='/api/maintenance/test-record':
            return self.send_json({'error':'not found'},404)
        if not may_publish_cure_record(mode(),self.headers.get('Authorization'),None):
            return self.send_json({'error':'IT diagnostic endpoint cannot publish quality records'},403)
        data=self.read_json()
        req,error=build_test_record(data)
        if error:return self.send_json({'error':error},400)
        now=time.monotonic()
        # Avoid burst abuse even in the deliberate training weakness.
        with GUARD:
            if now-LAST_REQUEST<0.4:return self.send_json({'error':'rate limit: try again later'},429)
            LAST_REQUEST=now
        payload=record(req['record_id'],req['result'])
        info=CLIENT.publish(RECORD_TOPIC,json.dumps(payload),qos=1)
        if info.rc!=0:return self.send_json({'error':'broker unavailable'},503)
        return self.send_json({'queued':True,'record_id':req['record_id'],
                               'mqtt_topic':RECORD_TOPIC},202)

if __name__=='__main__':
    CLIENT=client('gateway',on_connect,on_message)
    print('IT gateway listening on 8090. Mode=',mode(),flush=True)
    ThreadingHTTPServer(('0.0.0.0',8090),App).serve_forever()
