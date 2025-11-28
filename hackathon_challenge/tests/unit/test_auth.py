"""Unit tests for authentication layer.

Reference: implementation_plan.md §Phase 1 (Unit Tests)
"""

import pytest

# TODO: Import after implementation
# from hackathon_challenge.auth.socket import AuthenticatedSocket
# from hackathon_challenge.auth.exceptions import SecurityError, IntegrityError


class TestAuthenticatedSocket:
    """Test suite for AuthenticatedSocket."""

    def test_message_integrity(self, auth_key):
        """Test that valid messages pass authentication."""
        # TODO: Implement test
        pass

    def test_tampering_detection(self, auth_key):
        """Test that tampered messages raise SecurityError."""
        # TODO: Implement test
        pass

    def test_deterministic_serialization(self, auth_key):
        """Test that same message produces same HMAC."""
        # TODO: Implement test
        pass
