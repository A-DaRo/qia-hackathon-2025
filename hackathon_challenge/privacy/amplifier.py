"""Privacy amplification using Toeplitz hashing.

Reference:
- implementation_plan.md §Phase 4
- extending_qkd_technical_aspects.md §2.2
"""

from typing import List

import numpy as np
from scipy.linalg import toeplitz


class PrivacyAmplifier:
    """Toeplitz-matrix-based privacy amplification.

    Methods here never touch the SquidASM network; they operate entirely
    on local numpy arrays over GF(2).

    Notes
    -----
    Implements the Leftover Hash Lemma using 2-universal Toeplitz matrices.
    Reference: theoretical doc §4.2
    """

    def amplify(
        self,
        key: List[int],
        toeplitz_seed: List[int],
        new_length: int,
    ) -> List[int]:
        """Apply Toeplitz hashing for privacy amplification.

        Parameters
        ----------
        key : List[int]
            Reconciled and verified key bits.
        toeplitz_seed : List[int]
            Random seed defining the Toeplitz matrix.
        new_length : int
            Desired output key length.

        Returns
        -------
        List[int]
            Final secret key bits.

        Notes
        -----
        Computes K_sec = T × K_ver where T is a Toeplitz matrix.
        Matrix multiplication is performed modulo 2.
        """
        key_arr = np.array(key, dtype=np.uint8)
        
        # Construct Toeplitz matrix from seed
        col = toeplitz_seed[: len(key)]
        row = toeplitz_seed[len(key) - 1 :]
        T = toeplitz(col, row)[:new_length, :]
        
        # Matrix multiplication mod 2
        result = (T @ key_arr) % 2
        return result.astype(int).tolist()
