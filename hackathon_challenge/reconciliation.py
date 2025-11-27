from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, List

import numpy as np
from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

from hackathon_challenge.auth import AuthenticatedSocket


@dataclass
class PassHistory:
    """Stores parity information for backtracking across Cascade passes.

    Parameters
    ----------
    pass_index : int
        Index of the Cascade pass.
    block_index : int
        Index of the block within the pass.
    indices : List[int]
        Global key indices contained in this block.
    parity : int
        Parity (0 or 1) at the time it was last checked.
    """

    pass_index: int
    block_index: int
    indices: List[int]
    parity: int


class CascadeReconciliator:
    """Interactive Cascade implementation using an authenticated socket.

    This is a skeleton implementation intended to match the documentation.
    It focuses on API shape and generator usage; the internal Cascade logic
    should be completed as part of the challenge.
    """

    def __init__(
        self,
        socket: AuthenticatedSocket,
        is_alice: bool,
        key: List[int],
        rng_seed: int,
    ) -> None:
        self._socket = socket
        self._is_alice = is_alice
        self._key = np.array(key, dtype=np.uint8)
        self._rng_seed = rng_seed
        self._history: List[PassHistory] = []
        self._leakage_bits: int = 0

    def reconcile(self) -> Generator[EventExpression, None, int]:
        """Run all Cascade passes and return total parity leakage.

        All network operations inside this method must use ``yield from``.
        The caller must delegate with ``yield from reconciler.reconcile()``.
        """

        block_size = self._initial_block_size()
        # Skeleton: perform a fixed number of passes
        for pass_index in range(1):
            yield from self._run_pass(pass_index, block_size)

        return self._leakage_bits

    def get_key(self) -> List[int]:
        """Return the reconciled key as a Python list of bits."""

        return self._key.tolist()

    def _initial_block_size(self) -> int:
        return max(4, len(self._key) // 50) if len(self._key) > 0 else 0

    def _permute_indices(self, pass_index: int) -> np.ndarray:
        rng = np.random.RandomState(self._rng_seed + pass_index)
        indices = np.arange(len(self._key))
        rng.shuffle(indices)
        return indices

    def _run_pass(
        self, pass_index: int, block_size: int
    ) -> Generator[EventExpression, None, None]:
        """Run a single Cascade pass.

        This method currently only exchanges a dummy message to illustrate
        generator usage and message structure.
        """

        if len(self._key) == 0 or block_size <= 0:
            return None

        permuted = self._permute_indices(pass_index)
        # Example of a simple structured message exchange
        if self._is_alice:
            msg = StructuredMessage("CASCADE_PASS_INFO", {
                "pass_index": pass_index,
                "block_size": block_size,
                "num_bits": int(len(self._key)),
            })
            self._socket.send_structured(msg)
            _ = yield from self._socket.recv_structured()
        else:
            _ = yield from self._socket.recv_structured()
            ack = StructuredMessage("CASCADE_PASS_ACK", {"pass_index": pass_index})
            self._socket.send_structured(ack)

        _ = permuted  # avoid unused variable for now
        return None
