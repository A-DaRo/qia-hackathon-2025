"""Polynomial hashing over finite fields.

Reference:
- implementation_plan.md §Phase 3
- extending_qkd_theorethical_aspects.md §3.2
"""

from typing import List


def compute_polynomial_hash(key: List[int], salt: int, field_size: int) -> int:
    """Compute polynomial hash over GF(2^n).

    Parameters
    ----------
    key : List[int]
        Key bits to hash.
    salt : int
        Random salt (evaluation point).
    field_size : int
        Field size (e.g., 2^128).

    Returns
    -------
    int
        Hash tag.

    Notes
    -----
    Implements H_r(K) = Σ_{i=1}^L m_i * r^{L-i+1} mod p
    from theoretical doc §3.2.
    """
    # TODO: Implement polynomial hashing
    pass
