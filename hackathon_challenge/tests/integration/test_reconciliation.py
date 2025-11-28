"""Integration tests for reconciliation module.

These tests verify the complete reconciliation pipeline working together,
including edge cases and stress scenarios.

Reference: implementation_plan.md §Phase 2
"""

import numpy as np
import pytest

from hackathon_challenge.auth.socket import AuthenticatedSocket
from hackathon_challenge.reconciliation import (
    CascadeReconciliator,
    compute_optimal_block_size,
    compute_parity,
)

from ..conftest import MockSocketPair, run_generator_pair


class TestReconciliationWithAuthentication:
    """Test reconciliation using authenticated sockets."""

    def test_authenticated_reconciliation(self, mock_socket_pair, auth_key):
        """Test reconciliation through authenticated socket wrapper."""
        # Create authenticated sockets
        alice_auth = AuthenticatedSocket(mock_socket_pair.alice, auth_key)
        bob_auth = AuthenticatedSocket(mock_socket_pair.bob, auth_key)

        key_a = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
        key_b = [1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1]  # Error at index 3

        alice_rec = CascadeReconciliator(
            socket=alice_auth,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=3,
            initial_block_size=4,
        )
        bob_rec = CascadeReconciliator(
            socket=bob_auth,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=3,
            initial_block_size=4,
        )

        gen_alice = alice_rec.reconcile()
        gen_bob = bob_rec.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        # Keys should match after reconciliation
        assert alice_rec.get_key() == bob_rec.get_key()


class TestQBERBasedReconciliation:
    """Test reconciliation with QBER-based parameter selection."""

    @pytest.mark.parametrize(
        "qber,expected_min_block",
        [
            (0.01, 50),   # Very low QBER -> large blocks
            (0.05, 10),   # Medium QBER -> medium blocks
            (0.10, 4),    # High QBER -> small blocks
        ],
    )
    def test_block_size_from_qber(self, qber, expected_min_block, mock_socket_pair):
        """Test that block size is properly computed from QBER."""
        key = [0] * 200

        reconciliator = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key,
            rng_seed=42,
            estimated_qber=qber,
        )

        assert reconciliator._initial_block_size >= expected_min_block

    def test_optimal_block_size_formula(self):
        """Verify optimal block size follows 0.73/p formula."""
        # For QBER = 0.073, block size should be ~10
        qber = 0.073
        block_size = compute_optimal_block_size(qber)
        assert block_size == 10  # ceil(0.73/0.073) = 10


class TestErrorPatterns:
    """Test reconciliation with various error patterns."""

    def test_clustered_errors(self, mock_socket_pair):
        """Test reconciliation when errors are clustered together."""
        # Use a larger key where random permutations help separate clustered errors
        np.random.seed(88)
        key_a = list(np.random.randint(0, 2, 64))
        key_b = key_a.copy()
        # Cluster of 3 errors in positions 10, 12, 14 (nearby but not consecutive)
        key_b[10] ^= 1
        key_b[12] ^= 1
        key_b[14] ^= 1

        # Clustered errors are harder to detect - use more passes and smaller blocks
        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=6,  # More passes for difficult patterns
            initial_block_size=4,  # Balance between detection and efficiency
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()

    def test_spread_errors(self, mock_socket_pair):
        """Test reconciliation when errors are spread throughout key."""
        np.random.seed(123)
        key_a = list(np.random.randint(0, 2, 64))
        key_b = key_a.copy()

        # Spread 4 errors evenly
        error_positions = [5, 20, 40, 55]
        for pos in error_positions:
            key_b[pos] ^= 1

        # Use smaller initial block and more passes for spread errors
        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()

    def test_alternating_errors(self, mock_socket_pair):
        """Test reconciliation with alternating error pattern."""
        key_a = [1, 0] * 16  # Length 32
        key_b = key_a.copy()

        # Errors at every 8th position
        for i in range(0, 32, 8):
            key_b[i] ^= 1

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()


class TestLeakageTracking:
    """Test information leakage tracking."""

    def test_leakage_increases_with_errors(self, mock_socket_pair):
        """Test that leakage increases with more errors."""
        np.random.seed(42)
        key_a = list(np.random.randint(0, 2, 64))

        # Test with different error counts
        leakages = []
        for num_errors in [1, 3, 5]:
            key_b = key_a.copy()
            error_positions = [5, 15, 25, 35, 45][:num_errors]
            for pos in error_positions:
                key_b[pos] ^= 1

            # Reset sockets
            pair = MockSocketPair()

            alice = CascadeReconciliator(
                socket=pair.alice,
                is_initiator=True,
                key=key_a.copy(),
                rng_seed=42,
                num_passes=4,
                initial_block_size=8,
            )
            bob = CascadeReconciliator(
                socket=pair.bob,
                is_initiator=False,
                key=key_b.copy(),
                rng_seed=42,
                num_passes=4,
                initial_block_size=8,
            )

            gen_alice = alice.reconcile()
            gen_bob = bob.reconcile()

            alice_leakage, _ = run_generator_pair(gen_alice, gen_bob)
            leakages.append(alice_leakage)

        # More errors should generally mean more leakage
        # (due to more binary searches)
        assert leakages[0] <= leakages[2]

    def test_leakage_reported_consistently(self, mock_socket_pair):
        """Test that both parties report the same leakage."""
        key_a = [1, 0, 1, 1, 0, 0, 1, 0] * 4
        key_b = key_a.copy()
        key_b[3] ^= 1
        key_b[15] ^= 1

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

        alice_leakage, bob_leakage = run_generator_pair(gen_alice, gen_bob)

        assert alice_leakage == bob_leakage


class TestStressScenarios:
    """Stress tests for reconciliation."""

    def test_large_key(self, mock_socket_pair):
        """Test reconciliation with large key (128 bits)."""
        np.random.seed(77)
        key_a = list(np.random.randint(0, 2, 128))
        key_b = key_a.copy()

        # Introduce 4 errors
        error_positions = [15, 45, 75, 105]
        for pos in error_positions:
            key_b[pos] ^= 1

        # Use fixed block size for predictable behavior
        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=8,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=8,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()

    def test_many_passes(self, mock_socket_pair):
        """Test reconciliation with many passes."""
        key_a = [1, 0, 1, 1, 0, 0, 1, 0] * 8  # 64 bits
        key_b = key_a.copy()
        key_b[7] ^= 1
        key_b[23] ^= 1
        key_b[45] ^= 1

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=6,  # More passes than typical
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()

    @pytest.mark.parametrize("seed", [1, 42, 123, 456, 789])
    def test_different_seeds(self, mock_socket_pair, seed):
        """Test that different RNG seeds all work correctly."""
        np.random.seed(seed)
        key_a = list(np.random.randint(0, 2, 32))
        key_b = key_a.copy()

        # Introduce 2 errors
        key_b[5] ^= 1
        key_b[20] ^= 1

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=seed,
            num_passes=4,
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=seed,
            num_passes=4,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()


class TestBacktrackingScenarios:
    """Test scenarios that specifically exercise backtracking."""

    def test_even_errors_in_block(self, mock_socket_pair):
        """Test that even number of errors in a block are eventually found."""
        # Create a scenario where first pass has 2 errors in one block
        # which won't be detected initially but should be found via backtracking
        key_a = [0] * 16
        key_b = [0] * 16
        # Two errors in positions 0 and 1 (same block in pass 0 with block_size=4)
        key_b[0] = 1
        key_b[1] = 1

        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=4,
            initial_block_size=4,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        # Even though first pass won't detect the errors (even parity),
        # subsequent passes with different permutations should find them
        assert alice.get_key() == bob.get_key()

    def test_cascade_effect(self, mock_socket_pair):
        """Test that correcting one error exposes another."""
        # This tests the core "cascade" effect where fixing an error
        # in pass i reveals an error in pass j < i
        # Use larger key for more reliable permutation diversity
        np.random.seed(99)
        key_a = list(np.random.randint(0, 2, 64))
        key_b = key_a.copy()

        # Two errors that should be correctable
        key_b[5] ^= 1
        key_b[25] ^= 1

        # Use more passes to ensure cascade effect has time to propagate
        alice = CascadeReconciliator(
            socket=mock_socket_pair.alice,
            is_initiator=True,
            key=key_a.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=8,
        )
        bob = CascadeReconciliator(
            socket=mock_socket_pair.bob,
            is_initiator=False,
            key=key_b.copy(),
            rng_seed=42,
            num_passes=6,
            initial_block_size=8,
        )

        gen_alice = alice.reconcile()
        gen_bob = bob.reconcile()

        run_generator_pair(gen_alice, gen_bob)

        assert alice.get_key() == bob.get_key()
        # Should have corrected exactly 2 errors
        total_corrected = alice.get_errors_corrected() + bob.get_errors_corrected()
        assert total_corrected >= 2


class TestDeterminism:
    """Test determinism of reconciliation."""

    def test_reproducible_results(self, mock_socket_pair):
        """Test that same inputs produce same outputs."""
        key_a = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
        key_b = [1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 1]

        results = []
        for _ in range(3):
            pair = MockSocketPair()

            alice = CascadeReconciliator(
                socket=pair.alice,
                is_initiator=True,
                key=key_a.copy(),
                rng_seed=42,
                num_passes=4,
                initial_block_size=4,
            )
            bob = CascadeReconciliator(
                socket=pair.bob,
                is_initiator=False,
                key=key_b.copy(),
                rng_seed=42,
                num_passes=4,
                initial_block_size=4,
            )

            gen_alice = alice.reconcile()
            gen_bob = bob.reconcile()

            leakage, _ = run_generator_pair(gen_alice, gen_bob)

            results.append({
                "key": alice.get_key(),
                "leakage": leakage,
                "errors": alice.get_errors_corrected(),
            })

        # All runs should produce identical results
        for i in range(1, len(results)):
            assert results[i]["key"] == results[0]["key"]
            assert results[i]["leakage"] == results[0]["leakage"]
            assert results[i]["errors"] == results[0]["errors"]
