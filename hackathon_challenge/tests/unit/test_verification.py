"""Unit tests for key verification.

Reference: implementation_plan.md §Phase 3 (Unit Tests)
"""

import pytest

# TODO: Import after implementation
# from hackathon_challenge.verification.verifier import KeyVerifier
# from hackathon_challenge.verification.polynomial_hash import compute_polynomial_hash


class TestPolynomialHash:
    """Test suite for polynomial hashing."""

    def test_hash_determinism(self, sample_key):
        """Test that same key+salt produces same hash."""
        # TODO: Implement test
        pass

    def test_collision_probability(self):
        """Test hash collision probability bounds."""
        # TODO: Implement test
        pass


class TestKeyVerifier:
    """Test suite for KeyVerifier."""

    def test_identical_keys_verify(self, sample_key):
        """Test that identical keys return True."""
        # TODO: Implement test
        pass

    def test_different_keys_fail(self, sample_key_with_errors):
        """Test that different keys return False with high probability."""
        # TODO: Implement test
        pass
