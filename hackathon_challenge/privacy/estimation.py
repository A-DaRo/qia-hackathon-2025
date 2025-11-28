"""QBER estimation functions.

Reference:
- implementation_plan.md §Phase 4
- extending_qkd_technical_aspects.md §2.1
"""


def estimate_qber_from_cascade(
    total_bits: int,
    sample_errors: int,
    cascade_errors: int,
) -> float:
    """Estimate QBER combining sample and Cascade errors.

    Parameters
    ----------
    total_bits : int
        Total number of sifted bits.
    sample_errors : int
        Errors found in sampling phase.
    cascade_errors : int
        Errors corrected during Cascade.

    Returns
    -------
    float
        Estimated QBER (0 to 1).

    Notes
    -----
    Implements integrated QBER estimation from theoretical doc §2.1.
    """
    return (sample_errors + cascade_errors) / max(1, total_bits)
