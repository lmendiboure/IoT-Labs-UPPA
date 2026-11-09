from gaps_student import missing_ranges

cases = [
    ([1, 2, 3], [(1, 3)], [], "all covered"),
    ([1, 2, 3, 4, 5, 6], [(1, 2), (5, 6)], [(3, 4)], "middle gap"),
    ([8, 9, 10, 11], [(9, 9)], [(8, 8), (10, 11)], "two gaps"),
    ([2, 3, 4, 5], [], [(2, 5)], "no cloud coverage"),
    ([1, 2, 4, 5], [(1, 1), (4, 4)], [(2, 2), (5, 5)], "only sequences observed locally"),
]
passed = 0
for local, covered, expected, label in cases:
    try:
        actual = missing_ranges(local, covered)
        okay = actual == expected
    except Exception as exc:
        actual, okay = str(exc), False
    print(f"{'PASS' if okay else 'FAIL'} {label}: expected={expected}, got={actual}")
    passed += okay
print(f"RESULT {passed}/{len(cases)}")
raise SystemExit(0 if passed == len(cases) else 1)
