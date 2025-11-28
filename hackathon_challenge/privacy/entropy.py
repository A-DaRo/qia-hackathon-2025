"""Binary entropy and key length calculation.

Reference:
- implementation_plan.md §Phase 4
- extending_qkd_theorethical_aspects.md Step 2 §3
"""

import numpy as np


def binary_entropy(p: float) -> float:
    """Compute binary entropy function h(p).

    Parameters
    ----------
    p : float
        Probability (0 ≤ p ≤ 1).

    Returns
    -------
    float
        Binary entropy h(p) = -p*log₂(p) - (1-p)*log₂(1-p).

    Notes
    -----
    Used to quantify information leakage from quantum channel.
    Reference: theoretical doc Step 2 §3.1
    """
    if p <= 0 or p >= 1:
        return 0.0
    return -p * np.log2(p) - (1 - p) * np.log2(1 - p)


def compute_final_key_length(
    reconciled_length: int,
    qber: float,
    leakage_ec: int,
    leakage_ver: int,
    epsilon_sec: float = 1e-12,
) -> int:
    """Compute final secret key length using Devetak-Winter formula.

    Parameters
    ----------
    reconciled_length : int
        Length of reconciled key after error correction.
    qber : float
        Quantum Bit Error Rate.
    leakage_ec : int
        Information leakage from error correction (bits).
    leakage_ver : int
        Information leakage from verification (bits).
    epsilon_sec : float, optional
        Security parameter (default 1e-12).

    Returns
    -------
    int
        Final secret key length (non-negative).

    Notes
    -----
    Formula: ℓ_sec ≈ n[1 - h(QBER)] - leak_EC - leak_ver - 2*log₂(1/ε_sec)
    Reference: theoretical doc Step 2 §3.3
    """
    security_margin = 2 * np.log2(1 / epsilon_sec)
    available = reconciled_length * (1 - binary_entropy(qber))
    final_length = available - leakage_ec - leakage_ver - security_margin
    return max(0, int(np.floor(final_length)))
