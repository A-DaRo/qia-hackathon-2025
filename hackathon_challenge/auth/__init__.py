"""Authentication package initialization.

This package provides authenticated communication for QKD protocols.

Reference:
- implementation_plan.md §Phase 1
- extending_qkd_technical_aspects.md §Step 3
"""

from hackathon_challenge.auth.exceptions import IntegrityError, SecurityError
from hackathon_challenge.auth.socket import AuthenticatedSocket

__all__ = [
    "AuthenticatedSocket",
    "SecurityError",
    "IntegrityError",
]
