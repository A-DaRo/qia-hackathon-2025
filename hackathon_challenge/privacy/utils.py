"""Toeplitz matrix utilities.

Reference:
- implementation_plan.md §Phase 4
- extending_qkd_theorethical_aspects.md §4.2
"""

import random
from typing import List


def generate_toeplitz_seed(key_length: int, final_length: int) -> List[int]:
    """Generate random seed for Toeplitz matrix.

    Parameters
    ----------
    key_length : int
        Length of input key.
    final_length : int
        Length of output key.

    Returns
    -------
    List[int]
        Random seed bits (length = key_length + final_length - 1).

    Notes
    -----
    A Toeplitz matrix is fully defined by its first row and first column,
    requiring key_length + final_length - 1 bits total.
    """
    seed_length = key_length + final_length - 1
    return [random.randint(0, 1) for _ in range(seed_length)]
