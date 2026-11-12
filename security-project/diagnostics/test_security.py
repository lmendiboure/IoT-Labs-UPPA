"""Local unit tests of policy and ledger semantics. No broker required."""
import sys
sys.path.insert(0,'/app')
from policy import build_test_record, may_publish_cure_record, may_read_config
from state import State
from shared import TEMP_TOPIC, RECORD_TOPIC
import json
import unittest

class TestPolicy(unittest.TestCase):
    def test_valid_record(self):
        val,error=build_test_record({'record_id':'CR-AUDIT-1','result':'FAIL'})
        self.assertIsNone(error);self.assertEqual(val['result'],'FAIL')
    def test_invalid_record(self):
        for x in [None,{}, {'record_id':'bad','result':'PASS'},
                  {'record_id':'CR-1','result':'MAYBE'}]:
            self.assertIsNotNone(build_test_record(x)[1])
    def test_modes(self):
        self.assertTrue(may_publish_cure_record('vulnerable',None,None))
        self.assertFalse(may_publish_cure_record('hardened',None,None))
        self.assertTrue(may_read_config('vulnerable',None,None))
        self.assertFalse(may_read_config('hardened',None,None))
    def test_receipts_are_separate(self):
        s=State()
        s.ingest(TEMP_TOPIC,json.dumps({'temperature':180}))
        s.ingest(RECORD_TOPIC,json.dumps({'record_id':'CR-1'}))
        v=s.snapshot();self.assertEqual(v['counters']['temperature'],1)
        self.assertEqual(v['counters']['cure_records'],1)
        self.assertEqual(v['events'][0]['payload']['record_id'],'CR-1')
    def test_malformed_payload(self):
        s=State();s.ingest(RECORD_TOPIC,b'{bad}')
        self.assertEqual(s.snapshot()['counters']['invalid'],1)

if __name__=='__main__':unittest.main(verbosity=2)
