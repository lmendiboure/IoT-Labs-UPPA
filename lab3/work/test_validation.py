"""Offline acceptance checks for the student's Q15 screening function."""
import math
from validate_student import assess

base = {'device_id': 'AC-1', 'temperature_c': 179.8,
        'measured_at': '2026-10-01T12:00:00+00:00'}

cases = [
    ('nominal', base, True),
    ('outside physical range', dict(base, temperature_c=999), False),
    ('boolean temperature', dict(base, temperature_c=True), False),
    ('not a number', dict(base, temperature_c='179.8'), False),
    ('missing temperature', {'device_id': 'AC-1'}, False),
    ('wrong device claim', dict(base, device_id='UNKNOWN'), False),
    ('nonfinite number', dict(base, temperature_c=math.inf), False),
    ('not a JSON object', [base], False),
]

bad = 0
for name, data, expected in cases:
    try:
        accepted, reason = assess(data)
        passed = isinstance(accepted, bool) and accepted == expected
    except Exception as exc:
        accepted, reason, passed = None, f'exception: {exc}', False
    print(f'{"PASS" if passed else "FAIL"} {name:24} accepted={accepted!s:5} {reason}')
    bad += not passed
print(f'{len(cases)-bad}/{len(cases)} validation checks passed')
raise SystemExit(0 if not bad else 1)
