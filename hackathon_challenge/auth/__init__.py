"""Authentication package initialization."""

from hackathon_challenge.auth.exceptions import SecurityError, IntegrityError

__all__ = [
    "SecurityError",
    "IntegrityError",
]
