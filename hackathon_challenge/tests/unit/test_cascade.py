"""Unit tests for Cascade reconciliation.

Reference: implementation_plan.md §Phase 2 (Unit Tests)
"""

import numpy as np
import pytest

from hackathon_challenge.reconciliation.binary_search import (
    binary_search_initiator,
    binary_search_responder,
    calculate_binary_search_leakage,
)
from hackathon_challenge.reconciliation.cascade import CascadeReconciliator
from hackathon_challenge.reconciliation.history import BacktrackManager, PassHistory
from hackathon_challenge.reconciliation.utils import (
    compute_parity,
    permute_indices,
    split_into_blocks,
)

from ..conftest import MockSocketPair, run_generator_pair


class TestPassHistory:
    """Test suite for PassHistory dataclass."""

    def test_creation(self):
        """Test PassHistory creation."""
        history = PassHistory(
            pass_index=0, block_index=1, indices=[0, 1, 2, 3], parity=1
        )
        assert history.pass_index == 0
        assert history.block_index == 1
        assert history.indices == [0, 1, 2, 3]
        assert history.parity == 1

    def test_contains_index(self):
        """Test contains_index method."""
        history = PassHistory(
            pass_index=0, block_index=0, indices=[2, 5, 8, 11], parity=0
        )
        assert history.contains_index(2) is True
        assert history.contains_index(5) is True
        assert history.contains_index(0) is False
        assert history.contains_index(10) is False

    def test_flip_parity(self):
        """Test flip_parity method."""
        history = PassHistory(
            pass_index=0, block_index=0, indices=[0, 1], parity=0
        )
        assert history.parity == 0
        history.flip_parity()
        assert history.parity == 1
        history.flip_parity()
        assert history.parity == 0


class TestBacktrackManager:
    """Test suite for BacktrackManager."""

    def test_initialization(self):
        """Test BacktrackManager initialization."""
        manager = BacktrackManager(num_passes=4)
        assert manager.num_passes == 4
        for i in range(4):
            assert manager.get_blocks_for_pass(i) == []

    def test_record_block(self):
        """Test recording blocks."""
        manager = BacktrackManager(num_passes=3)
        manager.record_block(pass_index=0, block_index=0, indices=[0, 1, 2, 3], parity=1)
        manager.record_block(pass_index=0, block_index=1, indices=[4, 5, 6, 7], parity=0)

        blocks = manager.get_blocks_for_pass(0)
        assert len(blocks) == 2
        assert blocks[0].indices == [0, 1, 2, 3]
        assert blocks[1].indices == [4, 5, 6, 7]

    def test_find_affected_blocks(self):
        """Test finding affected blocks for backtracking."""
        manager = BacktrackManager(num_passes=3)

        # Pass 0: blocks [0,1,2,3] and [4,5,6,7]
        manager.record_block(0, 0, [0, 1, 2, 3], parity=0)
        manager.record_block(0, 1, [4, 5, 6, 7], parity=1)

        # Pass 1: blocks (after permutation) might contain different indices
        manager.record_block(1, 0, [0, 2, 4, 6], parity=0)
        manager.record_block(1, 1, [1, 3, 5, 7], parity=1)

        # If we're in pass 2 and flip index 2, find affected blocks in passes 0 and 1
        affected = manager.find_affected_blocks(flipped_index=2, current_pass=2)

        # Should find blocks in pass 0 (indices [0,1,2,3]) and pass 1 (indices [0,2,4,6])
        assert len(affected) == 2
        affected_indices = [set(b.indices) for b in affected]
        assert {0, 1, 2, 3} in affected_indices
        assert {0, 2, 4, 6} in affected_indices

    def test_update_block_parity(self):
        """Test updating block parity."""
        manager = BacktrackManager(num_passes=2)
        manager.record_block(0, 0, [0, 1, 2, 3], parity=0)

        manager.update_block_parity(0, 0, new_parity=1)

        blocks = manager.get_blocks_for_pass(0)
        assert blocks[0].parity == 1

    def test_clear(self):
        """Test clearing all history."""
        manager = BacktrackManager(num_passes=2)
        manager.record_block(0, 0, [0, 1], parity=0)
        manager.record_block(1, 0, [0, 1], parity=1)

        manager.clear()

        assert manager.get_blocks_for_pass(0) == []
        assert manager.get_blocks_for_pass(1) == []


class TestBinarySearch:
    """Test suite for binary search protocol."""

    def test_calculate_leakage(self):
        """Test binary search leakage calculation."""
        # Block size 1 -> 0 bits (no search needed)
        assert calculate_binary_search_leakage(1) == 0
        # Block size 2 -> 1 bit
        assert calculate_binary_search_leakage(2) == 1
        # Block size 4 -> 2 bits
        assert calculate_binary_search_leakage(4) == 2
        # Block size 8 -> 3 bits
        assert calculate_binary_search_leakage(8) == 3
        # Block size 5 -> ceil(log2(5)) = 3 bits
        assert calculate_binary_search_leakage(5) == 3

    def test_binary_search_single_error(self, mock_socket_pair):
        """Test binary search locates single error."""
        # Keys with error at index 2
        # Convention: initiator flips to match responder
        alice_key = [1, 0, 0, 1]  # Alice (initiator) has 0 at index 2
        bob_key = [1, 0, 1, 1]    # Bob (responder) has 1 at index 2

        block_indices = [0, 1, 2, 3]

        # Create generators
        gen_alice = binary_search_initiator(
            mock_socket_pair.alice, block_indices, alice_key
        )
        gen_bob = binary_search_responder(
            mock_socket_pair.bob, block_indices, bob_key
        )

        # Run both generators
        alice_result, bob_result = run_generator_pair(gen_alice, gen_bob)

        # Both should find error at index 2
        assert alice_result == 2
        assert bob_result == 2

        # Alice (initiator) flips to match Bob (responder)
        # Alice's key should now have 1 at index 2, matching Bob
        assert alice_key[2] == 1
        assert bob_key[2] == 1  # Bob doesn't flip
        assert alice_key == bob_key

    def test_binary_search_first_position(self, mock_socket_pair):
        """Test binary search when error is at first position."""
        alice_key = [0, 0, 0, 0]
        bob_key = [1, 0, 0, 0]  # Error at index 0

        block_indices = [0, 1, 2, 3]

        gen_alice = binary_search_initiator(
            mock_socket_pair.alice, block_indices, alice_key
        )
        gen_bob = binary_search_responder(
            mock_socket_pair.bob, block_indices, bob_key
        )

        alice_result, bob_result = run_generator_pair(gen_alice, gen_bob)

        assert alice_result == 0
        assert bob_result == 0
        assert alice_key[0] == 1

    def test_binary_search_last_position(self, mock_socket_pair):
        """Test binary search when error is at last position."""
        alice_key = [0, 0, 0, 0]
        bob_key = [0, 0, 0, 1]  # Error at index 3

        block_indices = [0, 1, 2, 3]

        gen_alice = binary_search_initiator(
            mock_socket_pair.alice, block_indices, alice_key
        )
        gen_bob = binary_search_responder(
            mock_socket_pair.bob, block_indices, bob_key
        )

        alice_result, bob_result = run_generator_pair(gen_alice, gen_bob)

        assert alice_result == 3
        assert bob_result == 3

    def test_binary_search_larger_block(self, mock_socket_pair):
        """Test binary search on larger block."""
        alice_key = [0] * 16
        bob_key = [0] * 16
        bob_key[11] = 1  # Error at index 11

        block_indices = list(range(16))

        gen_alice = binary_search_initiator(
            mock_socket_pair.alice, block_indices, alice_key
        )
        gen_bob = binary_search_responder(
            mock_socket_pair.bob, block_indices, bob_key
        )

        alice_result, bob_result = run_generator_pair(gen_alice, gen_bob)

        assert alice_result == 11
        assert bob_result == 11

    def test_binary_search_non_contiguous_indices(self, mock_socket_pair):
        """Test binary search with non-contiguous block indices."""
        # This simulates permuted indices in later Cascade passes
        alice_key = [0, 1, 0, 1, 0, 1, 0, 1]
        bob_key = [0, 1, 0, 1, 1, 1, 0, 1]  # Error at index 4

        # Non-contiguous block (e.g., after permutation)
        block_indices = [0, 2, 4, 6]

        gen_alice = binary_search_initiator(
            mock_socket_pair.alice, block_indices, alice_key
        )
        gen_bob = binary_search_responder(
            mock_socket_pair.bob, block_indices, bob_key
        )

        alice_result, bob_result = run_generator_pair(gen_alice, gen_bob)

        assert alice_result == 4
        assert bob_result == 4

    def test_binary_search_empty_raises(self, mock_socket_pair):
        """Test that empty block raises ValueError."""
        key = [1, 0, 1, 0]
        with pytest.raises(ValueError, match="must not be empty"):
            gen = binary_search_initiator(mock_socket_pair.alice, [], key)
            next(gen)


class TestCascadeReconciliator:
    """Test suite for CascadeReconciliator."""

    def test_initialization(self, mock_socket_pair):
        """Test CascadeReconciliator initialization."""
        key = [1, 0, 1, 1, 0, 0, 1, 0]
        reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key,
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )

        assert reconciliator.get_leakage() == 0
        assert reconciliator.get_errors_corrected() == 0
        assert reconciliator.get_key() == key

    def test_initialization_with_qber(self, mock_socket_pair):
        """Test CascadeReconciliator with QBER-based block size."""
        key = [1, 0, 1, 1] * 25  # 100 bits
        reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key,
            rng_seed=42,
            estimated_qber=0.05,  # 5% QBER -> block size ~15
        )

        # Block size should be computed from QBER
        assert reconciliator._initial_block_size == 15

    def test_get_key_array(self, mock_socket_pair):
        """Test get_key_array returns numpy array."""
        key = [1, 0, 1, 1]
        reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key,
            rng_seed=42,
        )

        arr = reconciliator.get_key_array()
        assert isinstance(arr, np.ndarray)
        assert np.array_equal(arr, np.array([1, 0, 1, 1], dtype=np.uint8))

    def test_reconcile_identical_keys(self, mock_socket_pair):
        """Test reconciliation when keys are already identical."""
        key = [1, 0, 1, 1, 0, 0, 1, 0]

        alice_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=4,
        )
        bob_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=4,
        )

        gen_alice = alice_reconciliator.reconcile()
        gen_bob = bob_reconciliator.reconcile()

        alice_leakage, bob_leakage = run_generator_pair(gen_alice, gen_bob)

        # Keys should remain identical
        assert alice_reconciliator.get_key() == bob_reconciliator.get_key()
        # No errors should be corrected
        assert alice_reconciliator.get_errors_corrected() == 0
        assert bob_reconciliator.get_errors_corrected() == 0

    def test_reconcile_single_error(self, mock_socket_pair, sample_key_single_error):
        """Test reconciliation with single error."""
        key_a, key_b = sample_key_single_error

        alice_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=4,
        )
        bob_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=4,
        )

        gen_alice = alice_reconciliator.reconcile()
        gen_bob = bob_reconciliator.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        # Keys should now match
        assert alice_reconciliator.get_key() == bob_reconciliator.get_key()

    def test_reconcile_multiple_errors(self, mock_socket_pair, sample_key_with_errors):
        """Test reconciliation with multiple errors."""
        key_a, key_b = sample_key_with_errors

        alice_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )
        bob_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )

        gen_alice = alice_reconciliator.reconcile()
        gen_bob = bob_reconciliator.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        # Keys should now match
        assert alice_reconciliator.get_key() == bob_reconciliator.get_key()

    def test_reconcile_tracks_leakage(self, mock_socket_pair, sample_key_single_error):
        """Test that reconciliation tracks information leakage."""
        key_a, key_b = sample_key_single_error

        alice_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=4,
        )
        bob_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=4,
        )

        gen_alice = alice_reconciliator.reconcile()
        gen_bob = bob_reconciliator.reconcile()

        alice_leakage, bob_leakage = run_generator_pair(gen_alice, gen_bob)

        # Both should report same leakage
        assert alice_leakage == bob_leakage
        assert alice_leakage > 0  # Some parity bits were exchanged

    def test_reconcile_long_key(self, mock_socket_pair, long_key_with_errors):
        """Test reconciliation with longer key and multiple errors."""
        key_a, key_b, error_positions = long_key_with_errors

        alice_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=8,
        )
        bob_reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=8,
        )

        gen_alice = alice_reconciliator.reconcile()
        gen_bob = bob_reconciliator.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        # Keys should now match
        final_alice = alice_reconciliator.get_key()
        final_bob = bob_reconciliator.get_key()
        assert final_alice == final_bob

    def test_deterministic_permutations(self, mock_socket_pair):
        """Test that permutations are deterministic across runs."""
        key = [1, 0, 1, 1, 0, 0, 1, 0] * 4

        # Create two reconciliators with same seed
        rec1 = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key.copy(),
            rng_seed=12345,
            num_passes=3,
        )
        rec2 = CascadeReconciliator(
            socket=mock_socket_pair.bob,  # Different socket, same seed
            is_initiator=False,
            key=key.copy(),
            rng_seed=12345,
            num_passes=3,
        )

        # Run reconciliation to populate permutations
        gen1 = rec1.reconcile()
        gen2 = rec2.reconcile()
        run_generator_pair(gen1, gen2)

        # Permutations should match
        for i in range(3):
            assert np.array_equal(
                rec1._pass_permutations[i], rec2._pass_permutations[i]
            )


class TestParityComputation:
    """Additional tests for parity computation in context of Cascade."""

    def test_parity_with_permuted_indices(self):
        """Test parity computation with permuted indices."""
        key = np.array([1, 0, 1, 1, 0, 0, 1, 0])

        # Original block [0, 1, 2, 3]
        parity1 = compute_parity(key, [0, 1, 2, 3])

        # Same bits but indices from permutation
        perm = permute_indices(8, seed=42, pass_idx=0)
        # Find which permuted positions map to original [0, 1, 2, 3]
        block_in_perm_space = [int(perm[i]) for i in range(4)]
        parity2 = compute_parity(key, block_in_perm_space)

        # Both should give valid parities (not necessarily equal)
        assert parity1 in [0, 1]
        assert parity2 in [0, 1]

    def test_block_parity_changes_with_bit_flip(self):
        """Test that block parity changes when a bit is flipped."""
        key = np.array([1, 0, 1, 1, 0, 0, 1, 0])
        indices = [0, 1, 2, 3]

        original_parity = compute_parity(key, indices)

        # Flip bit at index 2
        key[2] ^= 1

        new_parity = compute_parity(key, indices)

        # Parity should have changed
        assert new_parity != original_parity


class TestEdgeCases:
    """Test edge cases in reconciliation."""

    def test_minimum_key_length(self, mock_socket_pair):
        """Test reconciliation with minimum viable key length."""
        key_a = [1, 0, 1, 1]
        key_b = [1, 1, 1, 1]  # One error

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=2,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=2,
            initial_block_size=2,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()

    def test_all_zeros_key(self, mock_socket_pair):
        """Test reconciliation with all-zeros key."""
        key_a = [0] * 16
        key_b = [0] * 16
        key_b[7] = 1  # Single error

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=3,
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=3,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()

    def test_all_ones_key(self, mock_socket_pair):
        """Test reconciliation with all-ones key."""
        key_a = [1] * 16
        key_b = [1] * 16
        key_b[3] = 0  # Single error

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=3,
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=3,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()
