"""Base classes and dataclasses for QKD protocol.

Reference: implementation_plan.md §Phase 0
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CascadeConfig:
    """Configuration for Cascade reconciliation.

    Attributes
    ----------
    num_passes : int
        Number of Cascade passes (typically 4).
    initial_block_size : Optional[int]
        Initial block size for first pass. If None, computed from QBER.
    rng_seed : int
        Shared random seed for deterministic permutations.
    """

    num_passes: int = 4
    initial_block_size: Optional[int] = None
    rng_seed: int = 42


@dataclass
class PrivacyConfig:
    """Configuration for privacy amplification.

    Attributes
    ----------
    security_parameter : float
        Security parameter ε_sec (default 1e-12).
    compression_factor : float
        Safety margin for key length calculation (0.8-0.9).
    """

    security_parameter: float = 1e-12
    compression_factor: float = 0.8


@dataclass
class QKDResult:
    """Result of a QKD protocol run.

    Attributes
    ----------
    secret_key : List[int]
        Final secret key bits.
    qber : float
        Estimated Quantum Bit Error Rate.
    key_length : int
        Length of the final secret key.
    leakage : int
        Total information leakage (EC + verification).
    success : bool
        Whether the protocol completed successfully.
    error_message : Optional[str]
        Error message if protocol failed.
    """

    secret_key: List[int]
    qber: float
    key_length: int
    leakage: int
    success: bool
    error_message: Optional[str] = None
