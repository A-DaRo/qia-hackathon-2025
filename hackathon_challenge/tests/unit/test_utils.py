"""Unit tests for utility functions.

Reference: implementation_plan.md §Phase 0 and §Phase 2
"""

import numpy as np
import pytest

from hackathon_challenge.reconciliation.utils import (
    apply_permutation_to_key,
    compute_optimal_block_size,
    compute_parity,
    inverse_permutation,
    permute_indices,
    split_into_blocks,
)
from hackathon_challenge.utils.math import xor_bits


class TestXORBits:
    """Test suite for XOR operation."""

    def test_even_ones(self):
        """Test XOR of even number of 1s returns 0."""
        assert xor_bits([1, 1]) == 0
        assert xor_bits([1, 1, 1, 1]) == 0
        assert xor_bits([0, 0, 1, 1]) == 0

    def test_odd_ones(self):
        """Test XOR of odd number of 1s returns 1."""
        assert xor_bits([1]) == 1
        assert xor_bits([1, 1, 1]) == 1
        assert xor_bits([0, 0, 1]) == 1

    def test_empty_list(self):
        """Test XOR of empty list returns 0."""
        assert xor_bits([]) == 0

    def test_all_zeros(self):
        """Test XOR of all zeros returns 0."""
        assert xor_bits([0, 0, 0, 0]) == 0


class TestComputeParity:
    """Test suite for parity computation."""

    def test_even_parity_numpy(self):
        """Test parity of even number of 1s with numpy array."""
        key = np.array([1, 0, 1, 1, 0])
        # indices [0, 2] -> bits [1, 1] -> parity 0
        assert compute_parity(key, [0, 2]) == 0

    def test_odd_parity_numpy(self):
        """Test parity of odd number of 1s with numpy array."""
        key = np.array([1, 0, 1, 1, 0])
        # indices [0, 2, 3] -> bits [1, 1, 1] -> parity 1
        assert compute_parity(key, [0, 2, 3]) == 1

    def test_parity_with_list_input(self):
        """Test parity computation with list input."""
        key = [1, 0, 1, 1, 0]
        assert compute_parity(key, [0, 1]) == 1  # 1 XOR 0 = 1
        assert compute_parity(key, [1, 4]) == 0  # 0 XOR 0 = 0

    def test_single_index(self):
        """Test parity of single index."""
        key = np.array([1, 0, 1])
        assert compute_parity(key, [0]) == 1
        assert compute_parity(key, [1]) == 0

    def test_full_key_parity(self):
        """Test parity of entire key."""
        key = np.array([1, 0, 1, 1, 0])
        all_indices = list(range(len(key)))
        # 1 XOR 0 XOR 1 XOR 1 XOR 0 = 1
        assert compute_parity(key, all_indices) == 1

    def test_empty_indices_raises(self):
        """Test that empty indices raises ValueError."""
        key = np.array([1, 0, 1])
        with pytest.raises(ValueError, match="indices must not be empty"):
            compute_parity(key, [])

    def test_out_of_bounds_raises(self):
        """Test that out of bounds index raises IndexError."""
        key = np.array([1, 0, 1])
        with pytest.raises(IndexError):
            compute_parity(key, [0, 5])

    def test_negative_index_raises(self):
        """Test that negative index raises IndexError."""
        key = np.array([1, 0, 1])
        with pytest.raises(IndexError):
            compute_parity(key, [-1, 0])


class TestPermuteIndices:
    """Test suite for deterministic permutation."""

    def test_determinism_same_seed(self):
        """Test that same seed produces same permutation."""
        perm1 = permute_indices(10, seed=42, pass_idx=0)
        perm2 = permute_indices(10, seed=42, pass_idx=0)
        assert np.array_equal(perm1, perm2)

    def test_determinism_different_calls(self):
        """Test determinism across multiple calls."""
        for _ in range(5):
            perm = permute_indices(100, seed=12345, pass_idx=2)
            assert len(perm) == 100
            assert set(perm) == set(range(100))

    def test_different_seeds_different_permutations(self):
        """Test that different seeds produce different permutations."""
        perm1 = permute_indices(10, seed=42, pass_idx=0)
        perm2 = permute_indices(10, seed=43, pass_idx=0)
        assert not np.array_equal(perm1, perm2)

    def test_different_passes_different_permutations(self):
        """Test that different pass indices produce different permutations."""
        perm1 = permute_indices(10, seed=42, pass_idx=0)
        perm2 = permute_indices(10, seed=42, pass_idx=1)
        perm3 = permute_indices(10, seed=42, pass_idx=2)
        assert not np.array_equal(perm1, perm2)
        assert not np.array_equal(perm1, perm3)
        assert not np.array_equal(perm2, perm3)

    def test_permutation_is_valid(self):
        """Test that permutation contains all indices exactly once."""
        perm = permute_indices(20, seed=99, pass_idx=0)
        assert len(perm) == 20
        assert set(perm) == set(range(20))

    def test_invalid_length_raises(self):
        """Test that length < 1 raises ValueError."""
        with pytest.raises(ValueError, match="length must be >= 1"):
            permute_indices(0, seed=42, pass_idx=0)

    def test_length_one(self):
        """Test permutation of single element."""
        perm = permute_indices(1, seed=42, pass_idx=0)
        assert len(perm) == 1
        assert perm[0] == 0


class TestInversePermutation:
    """Test suite for inverse permutation computation."""

    def test_inverse_correctness(self):
        """Test that applying permutation then inverse gives identity."""
        perm = permute_indices(10, seed=42, pass_idx=0)
        inv = inverse_permutation(perm)

        # perm[inv[i]] should equal i
        for i in range(10):
            assert perm[inv[i]] == i

    def test_inverse_then_permutation(self):
        """Test that applying inverse then permutation gives identity."""
        perm = permute_indices(10, seed=42, pass_idx=0)
        inv = inverse_permutation(perm)

        # inv[perm[i]] should equal i
        for i in range(10):
            assert inv[perm[i]] == i

    def test_simple_case(self):
        """Test with a simple known permutation."""
        perm = np.array([2, 0, 1])  # 0->2, 1->0, 2->1
        inv = inverse_permutation(perm)
        assert np.array_equal(inv, np.array([1, 2, 0]))


class TestComputeOptimalBlockSize:
    """Test suite for optimal block size computation."""

    def test_low_qber(self):
        """Test block size for low QBER (e.g., 1%)."""
        # k₁ ≈ 0.73/0.01 = 73
        block_size = compute_optimal_block_size(0.01)
        assert block_size == 73

    def test_medium_qber(self):
        """Test block size for medium QBER (e.g., 5%)."""
        # k₁ ≈ 0.73/0.05 = 14.6 -> 15
        block_size = compute_optimal_block_size(0.05)
        assert block_size == 15

    def test_high_qber(self):
        """Test block size for high QBER near threshold (e.g., 10%)."""
        # k₁ ≈ 0.73/0.10 = 7.3 -> 8
        block_size = compute_optimal_block_size(0.10)
        assert block_size == 8

    def test_zero_qber_returns_large_block(self):
        """Test that zero QBER returns a large block size."""
        block_size = compute_optimal_block_size(0.0)
        assert block_size == 64

    def test_very_high_qber_returns_minimum(self):
        """Test that very high QBER returns minimum block size."""
        block_size = compute_optimal_block_size(0.5)
        assert block_size == 4

    def test_minimum_block_size(self):
        """Test that block size is at least 4."""
        # Very high QBER like 0.3 would give 0.73/0.3 ≈ 2.4
        # but minimum should be 4
        block_size = compute_optimal_block_size(0.25)
        assert block_size >= 4


class TestSplitIntoBlocks:
    """Test suite for splitting indices into blocks."""

    def test_exact_division(self):
        """Test splitting when length divides evenly."""
        blocks = split_into_blocks(12, 4)
        assert blocks == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]

    def test_remainder(self):
        """Test splitting with remainder."""
        blocks = split_into_blocks(10, 4)
        assert blocks == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]

    def test_block_larger_than_length(self):
        """Test when block size exceeds length."""
        blocks = split_into_blocks(3, 10)
        assert blocks == [[0, 1, 2]]

    def test_single_element(self):
        """Test splitting single element."""
        blocks = split_into_blocks(1, 4)
        assert blocks == [[0]]

    def test_empty_returns_empty(self):
        """Test splitting zero length returns empty list."""
        blocks = split_into_blocks(0, 4)
        assert blocks == []


class TestApplyPermutationToKey:
    """Test suite for applying permutation to key."""

    def test_basic_permutation(self):
        """Test basic permutation application."""
        key = np.array([1, 0, 1, 0])
        perm = np.array([3, 1, 0, 2])  # key[perm] = [key[3], key[1], key[0], key[2]]
        result = apply_permutation_to_key(key, perm)
        assert np.array_equal(result, np.array([0, 0, 1, 1]))

    def test_identity_permutation(self):
        """Test identity permutation leaves key unchanged."""
        key = np.array([1, 0, 1, 0])
        perm = np.array([0, 1, 2, 3])
        result = apply_permutation_to_key(key, perm)
        assert np.array_equal(result, key)

    def test_reverse_permutation(self):
        """Test reverse permutation."""
        key = np.array([1, 0, 1, 0])
        perm = np.array([3, 2, 1, 0])
        result = apply_permutation_to_key(key, perm)
        assert np.array_equal(result, np.array([0, 1, 0, 1]))

    def test_list_input(self):
        """Test with list input."""
        key = [1, 0, 1, 0]
        perm = np.array([2, 0, 3, 1])
        result = apply_permutation_to_key(key, perm)
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, np.array([1, 1, 0, 0]))
