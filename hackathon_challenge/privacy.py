from __future__ import annotations

from typing import List, Sequence

import numpy as np
from scipy.linalg import toeplitz


class PrivacyAmplifier:
    """Toeplitz-matrix-based privacy amplification.

    Methods here never touch the SquidASM network; they operate entirely on
    local numpy arrays over GF(2).
    """

    def amplify(
        self,
        key: Sequence[int],
        seed: Sequence[int],
        new_length: int,
    ) -> List[int]:
        """Compress a key using a Toeplitz matrix defined by ``seed``.

        Parameters
        ----------
        key : Sequence[int]
            Input key bits.
        seed : Sequence[int]
            Seed bits of length ``len(key) + new_length - 1``.
        new_length : int
            Desired output key length.

        Returns
        -------
        List[int]
            Compressed key bits.

        Raises
        ------
        ValueError
            If the seed length is inconsistent with ``key`` and
            ``new_length``.
        """

        key_arr = np.array(list(key), dtype=np.uint8)
        old_length = key_arr.size
        if len(seed) != old_length + new_length - 1:
            raise ValueError("Invalid seed length for Toeplitz construction")

        col = np.array(seed[:new_length], dtype=np.uint8)
        row = np.array(seed[new_length - 1 :], dtype=np.uint8)
        T = toeplitz(col, row)
        res = (T @ key_arr) % 2
        return res.astype(int).tolist()


def estimate_qber_from_cascade(
    total_bits: int,
    sample_errors: int,
    cascade_errors: int,
) -> float:
    """Estimate QBER from sampling and Cascade corrections.

    Parameters
    ----------
    total_bits : int
        Total number of bits in the (reconciled) key.
    sample_errors : int
        Number of errors observed in the initial sampling step.
    cascade_errors : int
        Number of bit flips performed during Cascade.

    Returns
    -------
    float
        Estimated quantum bit error rate.
    """

    if total_bits <= 0:
        return 0.0
    return (sample_errors + cascade_errors) / float(total_bits)
