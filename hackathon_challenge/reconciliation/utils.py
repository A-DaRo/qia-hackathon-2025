"""Utility functions for reconciliation.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_theorethical_aspects.md §2.2-2.4
"""

import math
from typing import List, Union

import numpy as np


def compute_parity(key: Union[np.ndarray, List[int]], indices: List[int]) -> int:
    """Compute parity (XOR) of bits at specified indices.

    Parameters
    ----------
    key : np.ndarray or List[int]
        Bit array (0s and 1s).
    indices : List[int]
        Indices to compute parity over.

    Returns
    -------
    int
        Parity bit (0 or 1).

    Raises
    ------
    ValueError
        If indices is empty.
    IndexError
        If any index is out of bounds.

    Notes
    -----
    Implements π(S) = ⊕_{i∈S} k_i mod 2 from theoretical doc §2.2.
    Uses numpy for efficient vectorized XOR when input is ndarray.

    Examples
    --------
    >>> key = np.array([1, 0, 1, 1, 0])
    >>> compute_parity(key, [0, 2, 3])  # 1 XOR 1 XOR 1 = 1
    1
    >>> compute_parity(key, [0, 1])  # 1 XOR 0 = 1
    1
    """
    if not indices:
        raise ValueError("indices must not be empty")

    key_arr = np.asarray(key, dtype=np.uint8)

    if len(indices) > 0 and (min(indices) < 0 or max(indices) >= len(key_arr)):
        raise IndexError(
            f"Index out of bounds: indices range [{min(indices)}, {max(indices)}] "
            f"for key of length {len(key_arr)}"
        )

    # Vectorized XOR: sum mod 2
    selected_bits = key_arr[indices]
    return int(np.sum(selected_bits) % 2)


def permute_indices(length: int, seed: int, pass_idx: int) -> np.ndarray:
    """Generate deterministic permutation of indices.

    Parameters
    ----------
    length : int
        Number of indices to permute.
    seed : int
        Shared RNG seed.
    pass_idx : int
        Pass index (used to derive different permutations per pass).

    Returns
    -------
    np.ndarray
        Permuted indices as int64 array.

    Raises
    ------
    ValueError
        If length < 1.

    Notes
    -----
    Must be deterministic: same seed+pass_idx → same permutation on both sides.
    The combined seed ensures different permutations per pass while maintaining
    reproducibility across Alice and Bob.

    Examples
    --------
    >>> perm1 = permute_indices(10, seed=42, pass_idx=0)
    >>> perm2 = permute_indices(10, seed=42, pass_idx=0)
    >>> np.array_equal(perm1, perm2)
    True
    >>> perm3 = permute_indices(10, seed=42, pass_idx=1)
    >>> np.array_equal(perm1, perm3)  # Different pass → different permutation
    False
    """
    if length < 1:
        raise ValueError(f"length must be >= 1, got {length}")

    # Combine seed and pass_idx for unique but deterministic permutation per pass
    combined_seed = seed * 1000 + pass_idx
    rng = np.random.default_rng(combined_seed)

    indices = np.arange(length, dtype=np.int64)
    rng.shuffle(indices)

    return indices


def inverse_permutation(permutation: np.ndarray) -> np.ndarray:
    """Compute the inverse of a permutation.

    Parameters
    ----------
    permutation : np.ndarray
        A permutation array where permutation[i] gives the new position of element i.

    Returns
    -------
    np.ndarray
        Inverse permutation where inverse[permutation[i]] = i.

    Examples
    --------
    >>> perm = np.array([2, 0, 1])
    >>> inv = inverse_permutation(perm)
    >>> inv
    array([1, 2, 0])
    """
    n = len(permutation)
    inverse = np.empty(n, dtype=permutation.dtype)
    inverse[permutation] = np.arange(n)
    return inverse


def compute_optimal_block_size(qber: float) -> int:
    """Compute optimal initial block size for Cascade given QBER.

    Parameters
    ----------
    qber : float
        Quantum Bit Error Rate estimate (0 < qber < 0.5).

    Returns
    -------
    int
        Optimal initial block size k₁.

    Notes
    -----
    From theoretical doc: k₁ ≈ 0.73/p for minimal leakage.
    We enforce a minimum of 4 to ensure meaningful parity blocks.

    References
    ----------
    Brassard & Salvail, "Secret-Key Reconciliation by Public Discussion"
    """
    if qber <= 0:
        # No errors expected, use large blocks
        return 64
    if qber >= 0.5:
        # Maximum error rate, use minimum blocks
        return 4

    # Optimal block size from Cascade theory: k₁ ≈ 0.73/p
    optimal = int(math.ceil(0.73 / qber))

    # Enforce minimum of 4 for meaningful binary search
    return max(4, optimal)


def split_into_blocks(length: int, block_size: int) -> List[List[int]]:
    """Split indices into blocks of specified size.

    Parameters
    ----------
    length : int
        Total number of indices to split.
    block_size : int
        Target block size.

    Returns
    -------
    List[List[int]]
        List of blocks, where each block is a list of indices.
        Last block may be smaller if length is not divisible by block_size.

    Examples
    --------
    >>> split_into_blocks(10, 4)
    [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]
    """
    blocks = []
    for start in range(0, length, block_size):
        end = min(start + block_size, length)
        blocks.append(list(range(start, end)))
    return blocks


def apply_permutation_to_key(
    key: Union[np.ndarray, List[int]], permutation: np.ndarray
) -> np.ndarray:
    """Apply permutation to key bits.

    Parameters
    ----------
    key : np.ndarray or List[int]
        Original key bits.
    permutation : np.ndarray
        Permutation array.

    Returns
    -------
    np.ndarray
        Permuted key bits.

    Examples
    --------
    >>> key = np.array([1, 0, 1, 0])
    >>> perm = np.array([3, 1, 0, 2])  # Maps: 0→3, 1→1, 2→0, 3→2
    >>> apply_permutation_to_key(key, perm)
    array([0, 0, 1, 1], dtype=uint8)
    """
    key_arr = np.asarray(key, dtype=np.uint8)
    return key_arr[permutation]
