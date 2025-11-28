"""Authentication-related exceptions.

Reference: implementation_plan.md §Phase 1
"""


class SecurityError(RuntimeError):
    """Raised when authentication or integrity checks fail."""

    pass


class IntegrityError(SecurityError):
    """Raised when HMAC verification fails."""

    pass
