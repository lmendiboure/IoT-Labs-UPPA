from summary_student import extra_fields

cases = [
    ([(1, 180), (2, 195), (3, 181)], {"maximum": 195, "peak_seq": 2}, "one peak"),
    ([(4, 191), (5, 191), (6, 180)], {"maximum": 191, "peak_seq": 4}, "first of tied peaks"),
    ([(10, -3.0), (11, -2.0)], {"maximum": -2.0, "peak_seq": 11}, "negative test values"),
    ([(13, 190)], {"maximum": 190, "peak_seq": 13}, "one sample"),
    ([(20, 180.5), (21, 183.25)], {"maximum": 183.25, "peak_seq": 21}, "decimal readings"),
]
passed = 0
for entries, expected, label in cases:
    try:
        actual = extra_fields(entries)
        okay = type(actual) is dict and actual == expected
    except Exception as err:
        actual, okay = str(err), False
    print(f"{'PASS' if okay else 'FAIL'} {label}: expected={expected}, got={actual}")
    passed += okay
print(f"RESULT {passed}/{len(cases)}")
raise SystemExit(0 if passed == len(cases) else 1)
