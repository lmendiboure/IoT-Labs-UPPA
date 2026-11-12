"""OT-side quality monitor: observes receipt, never asserts physical truth."""
from pathlib import Path
from http.server import ThreadingHTTPServer
from shared import client,TEMP_TOPIC,RECORD_TOPIC
from state import State
from httpkit import Handler

STATE=State()
HTML=Path('/app/quality.html').read_text(encoding='utf-8')

def on_connect(c,userdata,flags,reason_code,properties):
    if reason_code==0:c.subscribe([(TEMP_TOPIC,1),(RECORD_TOPIC,1)])

def on_message(c,userdata,msg): STATE.ingest(msg.topic,msg.payload)

class App(Handler):
    def do_GET(self):
        if self.path=='/':return self.send_html(HTML)
        if self.path=='/health':return self.send_json({'status':'ok'})
        if self.path=='/api/status':return self.send_json(STATE.snapshot())
        return self.send_json({'error':'not found'},404)

if __name__=='__main__':
    c=client('quality',on_connect,on_message)
    print('OT quality console listening on 8091',flush=True)
    ThreadingHTTPServer(('0.0.0.0',8091),App).serve_forever()
