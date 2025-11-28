"""Cascade error reconciliation protocol.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_technical_aspects.md §1.2
- extending_qkd_theorethical_aspects.md §2.4
"""

from typing import TYPE_CHECKING, Generator, List, Optional, Protocol, Union

import numpy as np
from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

from hackathon_challenge.core.constants import (
    DEFAULT_NUM_PASSES,
    MSG_CASCADE_PARITY,
)
from hackathon_challenge.reconciliation.binary_search import (
    binary_search_initiator,
    binary_search_responder,
    calculate_binary_search_leakage,
)
from hackathon_challenge.reconciliation.history import BacktrackManager, PassHistory
from hackathon_challenge.reconciliation.utils import (
    compute_optimal_block_size,
    compute_parity,
    permute_indices,
    split_into_blocks,
)

if TYPE_CHECKING:
    from hackathon_challenge.auth.socket import AuthenticatedSocket


class SocketProtocol(Protocol):
    """Protocol for socket-like objects supporting structured messages."""

    def send_structured(self, msg: StructuredMessage) -> None:
        """Send a structured message."""
        ...

    def recv_structured(
        self, **kwargs
    ) -> Generator[EventExpression, None, StructuredMessage]:
        """Receive a structured message."""
        ...


# Message headers for block parity exchange (separate from binary search)
MSG_BLOCK_PARITIES = "BLOCK_PARITIES"
MSG_PASS_COMPLETE = "PASS_COMPLETE"


class CascadeReconciliator:
    """Interactive Cascade implementation using an authenticated classical channel.

    Implements the multi-pass parity checking protocol with backtracking
    to correct errors between Alice's and Bob's keys.

    Parameters
    ----------
    socket : AuthenticatedSocket
        Authenticated classical channel to the peer.
    is_initiator : bool
        True if this party initiates parity exchanges and drives binary searches.
        Typically Alice is the initiator (is_initiator=True) and Bob responds.
    key : List[int]
        Local raw key bits (0/1) before reconciliation.
    rng_seed : int
        Shared permutation seed; must match on both parties.
    num_passes : int, optional
        Number of Cascade passes (default 4).
    initial_block_size : Optional[int], optional
        Initial block size. If None, computed from estimated QBER.
    estimated_qber : Optional[float], optional
        Estimated QBER for computing optimal block size.
        Only used if initial_block_size is None.

    Attributes
    ----------
    _leakage_bits : int
        Total parity bits exchanged (information leakage counter).
    _errors_corrected : int
        Total number of errors corrected during reconciliation.

    Notes
    -----
    Implements multi-pass parity checking with backtracking:
    - Pass 1: Small blocks to catch isolated errors
    - Subsequent passes: Larger blocks with permuted indices
    - Backtracking: When error corrected, check affected blocks in earlier passes

    Initial block size: k₁ ≈ 0.73/p for optimal efficiency (theoretical doc §2.4).
    Block size doubles each pass.

    Reference: extending_qkd_theorethical_aspects.md §2.4 (Cascade Protocol)
    """

    def __init__(
        self,
        socket: Union["AuthenticatedSocket", SocketProtocol],
        is_initiator: bool,
        key: List[int],
        rng_seed: int,
        num_passes: int = DEFAULT_NUM_PASSES,
        initial_block_size: Optional[int] = None,
        estimated_qber: Optional[float] = None,
    ) -> None:
        """Initialize Cascade reconciliator."""
        self._socket = socket
        self._is_initiator = is_initiator
        self._key = np.array(key, dtype=np.uint8)
        self._rng_seed = rng_seed
        self._num_passes = num_passes
        self._leakage_bits: int = 0
        self._errors_corrected: int = 0

        # Compute initial block size
        if initial_block_size is not None:
            self._initial_block_size = max(4, initial_block_size)
        elif estimated_qber is not None and estimated_qber > 0:
            self._initial_block_size = compute_optimal_block_size(estimated_qber)
        else:
            # Default heuristic: key_length / 50, but at least 4
            self._initial_block_size = max(4, len(self._key) // 50)

        # Initialize backtrack manager
        self._backtrack_manager = BacktrackManager(num_passes=num_passes)

        # Store permutations for all passes (for backtracking)
        self._pass_permutations: List[np.ndarray] = []
        self._pass_inverse_perms: List[np.ndarray] = []
        self._pass_block_sizes: List[int] = []

    def reconcile(self) -> Generator[EventExpression, None, int]:
        """Run all Cascade passes and return total parity leakage.

        Yields
        ------
        EventExpression
            Network operation events.

        Returns
        -------
        int
            Total information leakage in bits (parity bits exchanged).

        Notes
        -----
        Implements the full Cascade protocol:
        1. Multiple passes with increasing block sizes
        2. Parity exchange and binary search for error correction
        3. Backtracking to previous passes when errors are corrected

        All network operations use ``yield from`` for proper SquidASM integration.
        """
        block_size = self._initial_block_size

        # Pre-compute permutations for all passes
        for pass_idx in range(self._num_passes):
            perm = permute_indices(len(self._key), self._rng_seed, pass_idx)
            self._pass_permutations.append(perm)
            # Compute inverse permutation for backtracking
            inv_perm = np.empty_like(perm)
            inv_perm[perm] = np.arange(len(perm))
            self._pass_inverse_perms.append(inv_perm)
            self._pass_block_sizes.append(block_size)
            block_size *= 2

        # Reset block size for actual execution
        block_size = self._initial_block_size

        # Run each pass
        for pass_idx in range(self._num_passes):
            yield from self._run_pass(pass_idx, self._pass_block_sizes[pass_idx])

        return self._leakage_bits

    def get_key(self) -> List[int]:
        """Return the reconciled key as a Python list of bits.

        Returns
        -------
        List[int]
            Reconciled key bits.
        """
        return self._key.tolist()

    def get_key_array(self) -> np.ndarray:
        """Return the reconciled key as a numpy array.

        Returns
        -------
        np.ndarray
            Reconciled key bits as uint8 array.
        """
        return self._key.copy()

    def get_leakage(self) -> int:
        """Return total information leakage in bits.

        Returns
        -------
        int
            Number of parity bits exchanged.
        """
        return self._leakage_bits

    def get_errors_corrected(self) -> int:
        """Return total number of errors corrected.

        Returns
        -------
        int
            Number of bit errors that were found and corrected.
        """
        return self._errors_corrected

    def _run_pass(
        self, pass_index: int, block_size: int
    ) -> Generator[EventExpression, None, None]:
        """Execute a single Cascade pass.

        Parameters
        ----------
        pass_index : int
            Current pass index (0-indexed).
        block_size : int
            Block size for this pass.

        Yields
        ------
        EventExpression
            Network operation events.
        """
        # Get the permutation for this pass
        permutation = self._pass_permutations[pass_index]

        # Split into blocks of permuted indices
        # Each block contains the permuted indices
        blocks = split_into_blocks(len(self._key), block_size)

        # Convert block indices to original key indices via permutation
        # blocks[i] contains positions in the permuted view
        # permutation[blocks[i]] gives the original key indices
        original_blocks: List[List[int]] = []
        for block in blocks:
            original_indices = [int(permutation[i]) for i in block]
            original_blocks.append(original_indices)

        # Exchange parities for all blocks
        yield from self._exchange_and_correct_blocks(
            pass_index, original_blocks
        )

    def _exchange_and_correct_blocks(
        self, pass_index: int, blocks: List[List[int]]
    ) -> Generator[EventExpression, None, None]:
        """Exchange parities for all blocks and correct errors.

        Parameters
        ----------
        pass_index : int
            Current pass index.
        blocks : List[List[int]]
            List of blocks, each containing original key indices.

        Yields
        ------
        EventExpression
            Network operation events.
        """
        # Compute local parities for all blocks
        local_parities = [compute_parity(self._key, block) for block in blocks]

        if self._is_initiator:
            # Initiator sends parities first, then receives
            msg = StructuredMessage(MSG_BLOCK_PARITIES, local_parities)
            self._socket.send_structured(msg)

            response = yield from self._socket.recv_structured()
            if response.header != MSG_BLOCK_PARITIES:
                raise RuntimeError(f"Unexpected message: {response.header}")
            remote_parities = response.payload
        else:
            # Responder receives first, then sends
            response = yield from self._socket.recv_structured()
            if response.header != MSG_BLOCK_PARITIES:
                raise RuntimeError(f"Unexpected message: {response.header}")
            remote_parities = response.payload

            msg = StructuredMessage(MSG_BLOCK_PARITIES, local_parities)
            self._socket.send_structured(msg)

        # Count leakage (one parity bit per block from each side)
        self._leakage_bits += len(blocks)

        # Record all blocks in history for backtracking
        for block_idx, (block_indices, local_parity) in enumerate(
            zip(blocks, local_parities)
        ):
            self._backtrack_manager.record_block(
                pass_index=pass_index,
                block_index=block_idx,
                indices=block_indices,
                parity=local_parity,
            )

        # Find blocks with parity mismatch (odd number of errors)
        mismatched_blocks = []
        for block_idx, (local_p, remote_p) in enumerate(
            zip(local_parities, remote_parities)
        ):
            if local_p != remote_p:
                mismatched_blocks.append((block_idx, blocks[block_idx]))

        # Process each mismatched block with binary search
        for block_idx, block_indices in mismatched_blocks:
            error_idx = yield from self._binary_search_block(block_indices)

            if error_idx is not None:
                self._errors_corrected += 1
                # Perform backtracking
                yield from self._backtrack(error_idx, pass_index)

    def _binary_search_block(
        self, block_indices: List[int]
    ) -> Generator[EventExpression, None, Optional[int]]:
        """Run binary search on a block to find and correct one error.

        Parameters
        ----------
        block_indices : List[int]
            Indices of the block with odd parity mismatch.

        Yields
        ------
        EventExpression
            Network operation events.

        Returns
        -------
        Optional[int]
            Index of the corrected error, or None if block is too small.
        """
        if len(block_indices) == 0:
            return None

        if len(block_indices) == 1:
            # Single bit - flip it directly
            error_idx = block_indices[0]
            self._key[error_idx] ^= 1
            return error_idx

        # Add leakage for binary search
        self._leakage_bits += calculate_binary_search_leakage(len(block_indices))

        # Run binary search based on role
        if self._is_initiator:
            error_idx = yield from binary_search_initiator(
                self._socket, block_indices, self._key
            )
        else:
            error_idx = yield from binary_search_responder(
                self._socket, block_indices, self._key
            )

        return error_idx

    def _backtrack(
        self, flipped_index: int, current_pass: int
    ) -> Generator[EventExpression, None, None]:
        """Perform backtracking after correcting an error.

        When an error is corrected at `flipped_index`, check all blocks in
        earlier passes that contain this index. If their parity is now odd,
        they contain another error that was previously hidden.

        Parameters
        ----------
        flipped_index : int
            The key index that was just corrected.
        current_pass : int
            The current pass index (we only backtrack to earlier passes).

        Yields
        ------
        EventExpression
            Network operation events.

        Notes
        -----
        This implements the "cascade effect" from theoretical doc §2.4:
        "When an error is corrected in Pass i at index λ, it changes the
        parity of the block containing λ in all previous passes j < i."
        """
        # Find all affected blocks in earlier passes
        affected_blocks = self._backtrack_manager.find_affected_blocks(
            flipped_index, current_pass
        )

        for history_entry in affected_blocks:
            # The parity has changed due to the flip
            # Check if it's now odd (indicating another error)
            old_parity = history_entry.parity
            new_local_parity = compute_parity(self._key, history_entry.indices)

            # Update recorded parity
            self._backtrack_manager.update_block_parity(
                history_entry.pass_index,
                history_entry.block_index,
                new_local_parity,
            )

            # If parity changed from even to odd relative to remote,
            # we need to find another error
            # We can detect this by checking if local parity changed
            if new_local_parity != old_parity:
                # This block now has odd parity (one more visible error)
                # Run binary search to find it
                error_idx = yield from self._binary_search_block(history_entry.indices)

                if error_idx is not None:
                    self._errors_corrected += 1
                    # Recursive backtracking
                    yield from self._backtrack(error_idx, history_entry.pass_index)
