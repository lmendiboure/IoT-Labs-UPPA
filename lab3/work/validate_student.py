"""Application-level screening for the quality monitor.

This is an engineering exercise, not a trusted sensor attestation service.
Implement assess(data) in Q15. The source-supplied JSON can be fabricated even
when the MQTT client is authenticated and the connection uses TLS.
"""


def assess(data):
    """Return (accepted: bool, reason: str) for one decoded MQTT JSON value.

    Q15 requirements:
      - data is a JSON object (a Python dict)
      - device_id is the expected string 'AC-1'
      - temperature_c is a finite number (bool is NOT a valid number)
      - temperature_c is in [160, 200] degrees C for this demo scenario
      - a malformed payload must be rejected without crashing the monitor

    Optional extension: add timestamp freshness and persistent duplicate tracking.
    Do not mistake plausible for physically verified.
    """
    # TODO Q15: replace this default with your checks.
    return True, 'not yet validated'
