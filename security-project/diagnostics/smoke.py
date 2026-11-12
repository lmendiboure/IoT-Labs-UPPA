"""Non-destructive end-to-end regression: IT API, OT subscriber, real MQTT."""
import argparse
import json
import time
import urllib.request
import urllib.error


def request(url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=5) as resp:
            return resp.status,json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code,json.loads(e.read())


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--expect',choices=['vulnerable','hardened'],required=True)
    ap.add_argument('--it-url',default='http://gateway:8090')
    ap.add_argument('--ot-url',default='http://quality:8091')
    args=ap.parse_args()
    # Read a baseline so this check cannot pass on old, cached events after a restart.
    initial=None
    for i in range(12):
        try:
            sh, a=request(args.it_url+'/api/health')
            sq, snap=request(args.ot_url+'/api/status')
            sg, g=request(args.it_url+'/api/status')
            if sh==sq==sg==200:
                initial=(snap['counters'].copy(),g['counters'].copy())
                break
        except Exception:pass
        time.sleep(.5)
    if initial is None:raise SystemExit('FAIL: IT or OT HTTP endpoint not ready')
    for i in range(75):
        try:
            _,snap=request(args.ot_url+'/api/status')
            _,g=request(args.it_url+'/api/status')
            ready=all(snap['counters'][k]>initial[0][k] and
                      g['counters'][k]>initial[1][k]
                      for k in ('temperature','cure_records'))
            if ready:break
        except Exception:pass
        time.sleep(1)
    else:
        now_ot = snap.get('counters', {}) if isinstance(snap, dict) else {}
        now_it = g.get('counters', {}) if isinstance(g, dict) else {}
        raise SystemExit('FAIL: missing NEW legitimate temperature/cure record. '
                         f'OT baseline={initial[0]}, current={now_ot}; '
                         f'IT baseline={initial[1]}, current={now_it}. '
                         'Inspect broker/sensor/quality/gateway logs.')
    assert a['mode']==args.expect,(a,args.expect)
    st,config=request(args.it_url+'/api/config')
    expected=200 if args.expect=='vulnerable' else 403
    assert st==expected,('config access',st,expected)
    rid='CR-AUDIT-'+str(int(time.time()*1000)%10000000)
    # A student may have just used the interface: retry a bounded rate limit.
    for attempt in range(8):
        st,payload=request(args.it_url+'/api/maintenance/test-record',
                           {'record_id':rid,'result':'FAIL'})
        if st != 429: break
        time.sleep(0.3)
    expected=202 if args.expect=='vulnerable' else 403
    assert st==expected,('web->OT permission',st,expected,payload)
    if args.expect=='vulnerable':
        for _ in range(18):
            _,s=request(args.ot_url+'/api/status')
            if any(isinstance(ev.get('payload'),dict) and ev['payload'].get('record_id')==rid
                   for ev in s['events']):break
            time.sleep(.5)
        else:raise SystemExit('FAIL: OT quality board did not receive '+rid)
    else:
        # Negative proof: an HTTP denial must not have an OT-side effect.
        for _ in range(3):
            _,s=request(args.ot_url+'/api/status')
            if any(isinstance(ev.get('payload'),dict) and ev['payload'].get('record_id')==rid
                   for ev in s['events']):
                raise SystemExit('FAIL: denied web request still appeared in OT '+rid)
            time.sleep(.25)
    print('PASS',args.expect,'IT health, legitimate OT telemetry, config access, web-to-OT test',rid)

if __name__=='__main__': main()
