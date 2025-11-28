"""Protocol constants.

Reference:
- implementation_plan.md §Phase 0
- extending_qkd_theorethical_aspects.md Step 2 §2.2
"""

# Security parameters
QBER_THRESHOLD: float = 0.11  # Shor-Preskill bound (11%)
SECURITY_PARAMETER: float = 1e-12  # ε_sec for verification/PA
MIN_KEY_LENGTH: int = 100  # Minimum viable final key length

# Cascade protocol
CASCADE_EFFICIENCY: float = 1.15  # Typical efficiency factor (1.05-1.2)
DEFAULT_NUM_PASSES: int = 4  # Standard Cascade passes

# Verification
DEFAULT_TAG_BITS: int = 128  # Polynomial hash tag size (GF(2^128))

# Message headers for protocol communication
# Reference: extending_qkd_technical_aspects.md §1.3
MSG_CASCADE_REQ: str = "CASCADE_REQ"
MSG_CASCADE_PARITY: str = "CASCADE_PARITY"
MSG_CASCADE_DONE: str = "CASCADE_DONE"
MSG_VERIFY_HASH: str = "VERIFY_HASH"
MSG_PA_SEED: str = "PA_SEED"
MSG_ALL_MEASURED: str = "ALL_MEASURED"
