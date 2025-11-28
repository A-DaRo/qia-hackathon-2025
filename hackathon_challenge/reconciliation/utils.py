"""Utility functions for reconciliation.

Reference: implementation_plan.md §Phase 2
"""

from typing import List

import numpy as np


def compute_parity(key: np.ndarray, indices: List[int]) -> int:
    """Compute parity (XOR) of bits at specified indices.

    Parameters
    ----------
    key : np.ndarray
        Bit array (0s and 1s).
    indices : List[int]
        Indices to compute parity over.

    Returns
    -------
    int
        Parity bit (0 or 1).

    Notes
    -----
    Implements π(S) = ⊕_{i∈S} k_i mod 2 from theoretical doc §2.2
    """
    # TODO: Implement parity computation
    pass


def permute_indices(length: int, seed: int, pass_idx: int) -> np.ndarray:
    """Generate deterministic permutation of indices.

    Parameters
    ----------
    length : int
        Number of indices to permute.
    seed : int
        Shared RNG seed.
    pass_idx : int
        Pass index (used to derive different permutations).

    Returns
    -------
    np.ndarray
        Permuted indices.

    Notes
    -----
    Must be deterministic: same seed+pass_idx → same permutation on both sides.
    """
    # TODO: Implement deterministic permutation
    pass
