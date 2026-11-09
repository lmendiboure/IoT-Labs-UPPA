"""Optional Going deeper D: detect missing sample ranges after a WAN interruption."""


def missing_ranges(local_seqs, cloud_ranges):
    """Return sorted inclusive (first,last) intervals missing in the cloud.

    local_seqs: sequence numbers observed by the edge, e.g. [1,2,3,4,5,6]
    cloud_ranges: ranges covered by cloud raw events and/or aggregated windows,
                  e.g. [(1,2),(5,6)]
    Expected result in this example: [(3,4)]. Do not assume numbering starts at 1.
    """
    # TODO: build coverage from cloud_ranges; return consecutive missing intervals.
    return []
