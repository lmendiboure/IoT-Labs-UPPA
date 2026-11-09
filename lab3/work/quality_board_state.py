"""Simple presentation state for the Lab 3 quality application.

No MQTT credentials or network in this module. The board reports what the
application received; it cannot independently prove physical origin.
"""
from collections import deque
from datetime import datetime, timezone
from threading import Lock
import json

TEMPERATURE_TOPIC = 'plant/autoclave/AC-1/temperature'
CURE_TOPIC = 'quality/autoclave/AC-1/cure-records'


class QualityBoard:
    def __init__(self, *, validate=False):
        self.lock = Lock()
        self.validate = validate
        self.connected = False
        self.last_temperature = None
        self.last_cure = None
        self.counts = {'temperature': 0, 'cure_records': 0, 'rejected': 0}
        self.events = deque(maxlen=85)
        self.case_events = deque(maxlen=40)  # keep investigation records searchable
        self.event_id = 0

    def connection(self, connected, detail):
        with self.lock:
            self.connected = connected
            self._event('connection', 'INFO', detail, '')

    def _event(self, kind, verdict, summary, topic):
        self.event_id += 1
        item = {'id': self.event_id, 'at': datetime.now(timezone.utc).strftime('%H:%M:%S UTC'),
                'kind': kind, 'verdict': verdict, 'summary': str(summary), 'topic': topic}
        self.events.appendleft(item)
        return item

    def receive(self, topic, payload, validator=None):
        try:
            parsed = json.loads(payload)
        except (UnicodeDecodeError, TypeError, ValueError):
            parsed = None
        if topic == TEMPERATURE_TOPIC:
            if self.validate:
                if not isinstance(parsed, dict):
                    accepted, reason = False, 'invalid/non-object JSON'
                else:
                    try:
                        accepted, reason = validator(parsed)
                        if type(accepted) is not bool or not isinstance(reason, str):
                            raise ValueError('validator must return (bool, str)')
                    except Exception as exc:
                        accepted, reason = False, f'validator error: {exc}'
            else:
                accepted, reason = True, 'no application check enabled'
            value = parsed.get('temperature_c') if isinstance(parsed, dict) else None
            source_claim = parsed.get('device_id') if isinstance(parsed, dict) else None
            seq = parsed.get('seq') if isinstance(parsed, dict) else None
            with self.lock:
                self.counts['temperature'] += 1
                if accepted:
                    # Only accepted temperatures become the displayed current reading.
                    self.last_temperature = {
                        'value': value, 'source_claim': source_claim, 'seq': seq,
                        'verdict': 'DISPLAYED', 'reason': reason,
                    }
                else:
                    self.counts['rejected'] += 1
                # Rejections remain visible in the log without overwriting
                # the last accepted business value (and without hiding 999).
                return self._event('temperature', 'DISPLAYED' if accepted else 'REJECTED',
                    f'{value} °C · claimed {source_claim} · {reason}', topic)
        if topic == CURE_TOPIC:
            # Deliberately do not interpret receiving a record as proof of its validity.
            with self.lock:
                self.counts['cure_records'] += 1
                self.last_cure = {
                    'record_id': parsed.get('record_id') if isinstance(parsed, dict) else None,
                    'batch': parsed.get('batch') if isinstance(parsed, dict) else None,
                    'result': parsed.get('result') if isinstance(parsed, dict) else None,
                    'source_claim': parsed.get('device_id') if isinstance(parsed, dict) else None,
                    'verdict': 'UNVERIFIED',
                }
                event = self._event('cure record', 'UNVERIFIED',
                    f"{self.last_cure['record_id']} · result={self.last_cure['result']} · source unverified", topic)
                # A deliberately injected record remains searchable even when
                # ordinary simulator telemetry pushes it out of the live window.
                rid = self.last_cure['record_id']
                if isinstance(rid, str) and rid.startswith('CR-') and not rid.startswith('CR-SIM-'):
                    self.case_events.appendleft(event)
                return event
        return None

    def snapshot(self):
        with self.lock:
            return {'connected': self.connected, 'validate': self.validate,
                    'last_temperature': dict(self.last_temperature) if self.last_temperature else None,
                    'last_cure': dict(self.last_cure) if self.last_cure else None,
                    'counts': dict(self.counts), 'events': list(self.events),
                    'case_events': list(self.case_events)}
