"""Pytest configuration and shared fixtures.

Reference: implementation_plan.md §5 (Testing Strategy)
"""

import pytest


@pytest.fixture
def sample_key():
    """Provide a sample key for testing."""
    return [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1]


@pytest.fixture
def sample_key_with_errors():
    """Provide two keys with known error pattern."""
    key_a = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
    key_b = [1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1]  # 2 errors at indices 3, 7
    return key_a, key_b


@pytest.fixture
def auth_key():
    """Provide a sample authentication key."""
    return b"shared_secret_key_for_testing"


@pytest.fixture
def cascade_config():
    """Provide standard Cascade configuration."""
    return {
        "num_passes": 4,
        "initial_block_size": 4,
        "rng_seed": 42,
    }
