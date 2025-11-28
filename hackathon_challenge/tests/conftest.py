"""Pytest configuration and shared fixtures.

Reference: implementation_plan.md §5 (Testing Strategy)
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Generator, List, Optional, Tuple

import numpy as np
import pytest
from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression


@dataclass
class MockMessage:
    """A message in the mock socket queue."""

    header: str
    payload: Any


class MockSocket:
    """Mock socket for testing reconciliation protocols.

    This mock simulates the behavior of ClassicalSocket by maintaining
    separate send/receive queues. Two MockSocket instances can be linked
    together so that one's send goes to the other's receive.

    Parameters
    ----------
    name : str
        Name for debugging/logging.

    Attributes
    ----------
    _send_queue : Deque[StructuredMessage]
        Queue of messages to be sent.
    _recv_queue : Deque[StructuredMessage]
        Queue of received messages.
    _peer : Optional[MockSocket]
        Linked peer socket.
    """

    def __init__(self, name: str = "mock") -> None:
        self.name = name
        self._send_queue: Deque[StructuredMessage] = deque()
        self._recv_queue: Deque[StructuredMessage] = deque()
        self._peer: Optional["MockSocket"] = None
        self._waiting_for_message = False

    def link_peer(self, peer: "MockSocket") -> None:
        """Link this socket to a peer socket.

        Messages sent on this socket will appear in the peer's recv queue.

        Parameters
        ----------
        peer : MockSocket
            The peer socket to link.
        """
        self._peer = peer
        peer._peer = self

    def send_structured(self, msg: StructuredMessage) -> None:
        """Send a structured message.

        Parameters
        ----------
        msg : StructuredMessage
            Message to send.
        """
        if self._peer is not None:
            self._peer._recv_queue.append(msg)
        else:
            self._send_queue.append(msg)

    def recv_structured(
        self, **kwargs
    ) -> Generator[EventExpression, None, StructuredMessage]:
        """Receive a structured message.

        This is a generator that yields until a message is available.

        Yields
        ------
        EventExpression
            (Yields None to indicate waiting for message)

        Returns
        -------
        StructuredMessage
            The received message.
        """
        # Keep yielding while waiting for a message
        while not self._recv_queue:
            self._waiting_for_message = True
            yield None  # Signal that we're waiting
        
        self._waiting_for_message = False
        return self._recv_queue.popleft()

    def has_pending_message(self) -> bool:
        """Check if there's a message waiting to be received."""
        return len(self._recv_queue) > 0

    def is_waiting(self) -> bool:
        """Check if this socket is waiting for a message."""
        return self._waiting_for_message

    def queue_message(self, header: str, payload: Any) -> None:
        """Manually queue a message for receiving.

        Parameters
        ----------
        header : str
            Message header.
        payload : Any
            Message payload.
        """
        self._recv_queue.append(StructuredMessage(header, payload))

    def get_sent_messages(self) -> List[StructuredMessage]:
        """Get all messages in the send queue.

        Returns
        -------
        List[StructuredMessage]
            List of sent messages.
        """
        return list(self._send_queue)

    def clear_queues(self) -> None:
        """Clear all message queues."""
        self._send_queue.clear()
        self._recv_queue.clear()


class MockSocketPair:
    """A pair of linked mock sockets for testing.

    Creates two sockets where messages sent on one appear
    in the receive queue of the other.

    Attributes
    ----------
    alice : MockSocket
        Alice's socket.
    bob : MockSocket
        Bob's socket.
    """

    def __init__(self) -> None:
        self.alice = MockSocket("alice")
        self.bob = MockSocket("bob")
        self.alice.link_peer(self.bob)


def run_generator_pair(
    gen_alice: Generator, gen_bob: Generator
) -> Tuple[Any, Any]:
    """Run two generators that communicate via mock sockets.

    This helper alternates between the two generators, allowing them
    to exchange messages. Each generator is advanced until it either
    returns a result or yields.

    Parameters
    ----------
    gen_alice : Generator
        Alice's generator (typically initiator).
    gen_bob : Generator
        Bob's generator (typically responder).

    Returns
    -------
    Tuple[Any, Any]
        (alice_result, bob_result) when both generators complete.
    """
    alice_done = False
    bob_done = False
    alice_result = None
    bob_result = None

    # Alternate until both complete
    max_iterations = 10000
    iteration = 0

    while not (alice_done and bob_done) and iteration < max_iterations:
        iteration += 1

        # Advance Alice
        if not alice_done:
            try:
                next(gen_alice)
            except StopIteration as e:
                alice_done = True
                alice_result = e.value

        # Advance Bob
        if not bob_done:
            try:
                next(gen_bob)
            except StopIteration as e:
                bob_done = True
                bob_result = e.value

    if iteration >= max_iterations:
        raise RuntimeError("Generator pair did not complete within iteration limit")

    return alice_result, bob_result


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
def sample_key_single_error():
    """Provide two keys with a single error."""
    key_a = [1, 0, 1, 1, 0, 0, 1, 0]
    key_b = [1, 0, 1, 0, 0, 0, 1, 0]  # Error at index 3
    return key_a, key_b


@pytest.fixture
def long_key_with_errors():
    """Provide longer keys with multiple errors for stress testing."""
    np.random.seed(42)
    key_a = list(np.random.randint(0, 2, 100))
    key_b = key_a.copy()
    # Introduce 5 errors at random positions
    error_positions = [7, 23, 45, 67, 89]
    for pos in error_positions:
        key_b[pos] ^= 1
    return key_a, key_b, error_positions


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


@pytest.fixture
def mock_socket_pair():
    """Provide a pair of linked mock sockets."""
    return MockSocketPair()


@pytest.fixture
def mock_socket():
    """Provide a single mock socket."""
    return MockSocket("test")
