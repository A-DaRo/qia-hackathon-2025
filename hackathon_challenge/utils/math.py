"""Common mathematical operations.

Reference: implementation_plan.md §Phase 0
"""

from typing import List


def xor_bits(bits: List[int]) -> int:
    """Compute XOR of a list of bits.

    Parameters
    ----------
    bits : List[int]
        List of bits (0 or 1).

    Returns
    -------
    int
        XOR result (0 or 1).
    """
    result = 0
    for bit in bits:
        result ^= bit
    return result
