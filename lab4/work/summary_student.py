"""Lab 4 Q11: enrich an edge summary so the cloud can locate a brief peak."""


def extra_fields(window):
    """Return {'maximum': number, 'peak_seq': int}.

    window is a NONEMPTY ordered list of (sequence_number, temperature) tuples.
    For equal maximum temperatures, select the earliest sequence number.
    Example: [(1, 180), (2, 195), (3, 180)] ->
             {'maximum': 195, 'peak_seq': 2}.
    """
    # TODO: keep the largest temperature and its first sequence number.
    return {}
