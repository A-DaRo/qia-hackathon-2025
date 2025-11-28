"""QKD Extension Package.

This package implements an extended Quantum Key Distribution protocol with:
- Cascade error reconciliation
- Polynomial hash verification
- Toeplitz privacy amplification
- Wegman-Carter authentication

Reference: implementation_plan.md
"""

__version__ = "0.1.0"
__author__ = "QIA Hackathon 2025 Team"

from hackathon_challenge.core.constants import (
    QBER_THRESHOLD,
    MIN_KEY_LENGTH,
    SECURITY_PARAMETER,
)

__all__ = [
    "QBER_THRESHOLD",
    "MIN_KEY_LENGTH",
    "SECURITY_PARAMETER",
]
