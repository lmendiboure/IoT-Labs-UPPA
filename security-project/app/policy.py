"""Authorization policy for the IT diagnostic gateway."""
import re

VALID_ID=re.compile(r'^CR-[A-Z0-9-]{1,48}$')

def build_test_record(data):
    if not isinstance(data,dict): return None,'Expected JSON object'
    rid=data.get('record_id','')
    result=data.get('result')
    if not isinstance(rid,str) or not VALID_ID.fullmatch(rid):
        return None,'record_id must match CR-[A-Z0-9-]'
    if result not in ('PASS','FAIL'):
        return None,'result must be PASS or FAIL'
    return {'record_id':rid,'result':result},None


def may_publish_cure_record(mode, supplied_token, expected_token):
    if mode=='vulnerable':return True
    return False


def may_read_config(mode, supplied_token, expected_token):
    return mode=='vulnerable'
