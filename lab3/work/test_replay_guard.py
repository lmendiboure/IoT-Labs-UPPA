"""Offline tests for the optional replay guard; no broker or network required."""
from replay_guard_logic import first_occurrence

seen = set()
cases = [
    ('first CR-399', 'CR-399', True),
    ('repeated CR-399', 'CR-399', False),
    ('first CR-400', 'CR-400', True),
    ('repeated CR-400', 'CR-400', False),
]
passed = 0
for name, rid, expected in cases:
    result = first_occurrence(rid, seen)
    ok = type(result) is bool and result == expected
    print(f'{"PASS" if ok else "FAIL"} {name}: {result} (expected {expected})')
    passed += ok
print(f'{passed}/{len(cases)} replay-guard tests passed')
raise SystemExit(0 if passed == len(cases) else 1)
