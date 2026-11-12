"""Thread-safe application-side receipt log. Not a packet capture."""
from collections import deque
from threading import RLock
from shared import TEMP_TOPIC, RECORD_TOPIC, json_message

class State:
    def __init__(self):
        self.lock=RLock()
        self.events=deque(maxlen=160)
        self.counters={'temperature':0,'cure_records':0,'invalid':0}
    def ingest(self,topic,payload):
        data=json_message(payload)
        if topic==TEMP_TOPIC:kind='temperature'
        elif topic==RECORD_TOPIC:kind='cure_records'
        else: return
        with self.lock:
            if data is None: self.counters['invalid']+=1
            else: self.counters[kind]+=1
            self.events.appendleft({'kind':kind,'topic':topic,'payload':data,
                                    'valid_json':data is not None})
    def snapshot(self):
        with self.lock:
            return {'counters':dict(self.counters),'events':list(self.events)}
