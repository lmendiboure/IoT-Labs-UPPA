"""Lab 4 Q4–Q7: local detection rule. Complete step(), then run test_edge.py.

Rule: trigger ONE alert when the third consecutive sample strictly above
190 degrees Celsius arrives. A normal sample resets the counter. The counter
is capped at 3, so a fourth high sample does not trigger another alert.
These temperatures are only classroom examples, NOT industrial safety limits.
"""


def step(temperature, consecutive):
    """Return (new_consecutive_count: int, alert_now: bool).

    consecutive is the number of high samples immediately preceding this
    reading, capped at 3. The edge service keeps one state per run_id.
    """
    # TODO: Implement the rule. These placeholders are deliberately incorrect.
    return 0, False
