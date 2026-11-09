"""Seven offline checks. The student starter should FAIL some checks initially."""
from detect_student import step

cases = [
    (180, 0, (0, False), "normal reading"),
    (195, 0, (1, False), "first high reading"),
    (191, 1, (2, False), "second consecutive high reading"),
    (193, 2, (3, True), "third consecutive high reading"),
    (194, 3, (3, False), "fourth high reading: no repeated alert"),
    (180, 2, (0, False), "normal reading resets the count"),
    (190, 2, (0, False), "exact threshold is NOT above 190"),
]
passed = 0
for temperature, previous, expected, label in cases:
    try:
        observed = step(temperature, previous)
        ok = (type(observed) is tuple and len(observed) == 2 and
              type(observed[0]) is int and type(observed[1]) is bool and observed == expected)
    except Exception as exc:
        observed, ok = f"EXCEPTION {exc}", False
    passed += bool(ok)
    print(f"{'PASS' if ok else 'FAIL'} {label}: expected={expected} got={observed}")
print(f"RESULT {passed}/{len(cases)}")
raise SystemExit(0 if passed == len(cases) else 1)
