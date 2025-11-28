"""Binary search protocol for error localization in Cascade.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_theorethical_aspects.md §2.3 (BINARY primitive)
- extending_qkd_technical_aspects.md §1.3 (StructuredMessage protocol)
"""

from typing import TYPE_CHECKING, Generator, List, Protocol, Union

import numpy as np
from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

from hackathon_challenge.core.constants import (
    MSG_CASCADE_DONE,
    MSG_CASCADE_PARITY,
    MSG_CASCADE_REQ,
)
from hackathon_challenge.reconciliation.utils import compute_parity

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


def binary_search_initiator(
    socket: Union["AuthenticatedSocket", SocketProtocol],
    block_indices: List[int],
    key: Union[np.ndarray, List[int]],
) -> Generator[EventExpression, None, int]:
    """Execute binary search as initiator (drives the protocol).

    The initiator sends parity requests and determines which half contains
    the error. This role should be taken by one consistent party (e.g., Bob)
    to avoid deadlock.

    Parameters
    ----------
    socket : AuthenticatedSocket or SocketProtocol
        Authenticated classical channel to the peer.
    block_indices : List[int]
        Indices of the block containing an odd number of errors.
        Must be non-empty.
    key : np.ndarray or List[int]
        Local key bits.

    Yields
    ------
    EventExpression
        Network operation events from recv_structured calls.

    Returns
    -------
    int
        Index of the error bit that was located and flipped locally.

    Notes
    -----
    Implements the BINARY primitive from theoretical doc §2.3.
    Cost: ⌈log₂(k)⌉ parity bits exchanged for a block of size k.

    The protocol flow:
    1. Split block into halves
    2. Request parity of left half from responder
    3. Compare with local parity to determine which half has error
    4. Recurse until single bit found
    5. Flip the error bit locally
    6. Send CASCADE_DONE to notify responder

    Examples
    --------
    >>> # With mock socket (see tests)
    >>> error_idx = yield from binary_search_initiator(socket, [0, 1, 2, 3], key)
    """
    if not block_indices:
        raise ValueError("block_indices must not be empty")

    key_arr = np.asarray(key, dtype=np.uint8)
    left = 0
    right = len(block_indices)

    # Binary search to locate the error
    while right - left > 1:
        mid = (left + right) // 2
        left_half_indices = block_indices[left:mid]

        # Request parity of left half from responder
        request = StructuredMessage(MSG_CASCADE_REQ, left_half_indices)
        socket.send_structured(request)

        # Receive responder's parity
        response = yield from socket.recv_structured()
        if response.header != MSG_CASCADE_PARITY:
            raise RuntimeError(
                f"Unexpected message header: expected {MSG_CASCADE_PARITY}, "
                f"got {response.header}"
            )
        remote_left_parity = int(response.payload)

        # Compute local parity and compare
        local_left_parity = compute_parity(key_arr, left_half_indices)

        if local_left_parity != remote_left_parity:
            # Error is in the left half
            right = mid
        else:
            # Error is in the right half
            left = mid

    # Found the error index
    error_index = block_indices[left]

    # Flip the error bit locally
    key_arr[error_index] ^= 1

    # If key was passed as a mutable list, update it
    if isinstance(key, list):
        key[error_index] ^= 1

    # Notify responder that search is complete
    done_msg = StructuredMessage(MSG_CASCADE_DONE, error_index)
    socket.send_structured(done_msg)

    return error_index


def binary_search_responder(
    socket: Union["AuthenticatedSocket", SocketProtocol],
    block_indices: List[int],
    key: Union[np.ndarray, List[int]],
) -> Generator[EventExpression, None, int]:
    """Execute binary search as responder (answers parity queries).

    The responder waits for parity requests from the initiator and
    responds with local parities until the error is located.

    Parameters
    ----------
    socket : AuthenticatedSocket or SocketProtocol
        Authenticated classical channel to the peer.
    block_indices : List[int]
        Indices of the block containing an odd number of errors.
        Must match initiator's block (same indices).
    key : np.ndarray or List[int]
        Local key bits.

    Yields
    ------
    EventExpression
        Network operation events from recv_structured calls.

    Returns
    -------
    int
        Index of the error bit that was located (NOT flipped by responder).

    Notes
    -----
    The responder passively answers queries until receiving CASCADE_DONE.
    IMPORTANT: Only the initiator flips the error bit. The responder does NOT
    flip because both parties need to converge to the SAME value. Since we
    don't know which party is "correct", by convention the initiator (who
    drives the search) flips their bit to match the responder's value.

    The protocol flow:
    1. Wait for CASCADE_REQ with indices of a sub-block
    2. Compute and send local parity for those indices
    3. Repeat until CASCADE_DONE received
    4. Return the error index (DO NOT flip)
    """
    if not block_indices:
        raise ValueError("block_indices must not be empty")

    key_arr = np.asarray(key, dtype=np.uint8)

    while True:
        # Wait for request from initiator
        message = yield from socket.recv_structured()

        if message.header == MSG_CASCADE_REQ:
            # Initiator is asking for parity of a sub-block
            sub_block_indices = message.payload

            # Compute local parity
            local_parity = compute_parity(key_arr, sub_block_indices)

            # Send parity response
            response = StructuredMessage(MSG_CASCADE_PARITY, local_parity)
            socket.send_structured(response)

        elif message.header == MSG_CASCADE_DONE:
            # Initiator found the error
            error_index = int(message.payload)

            # DO NOT flip - only the initiator flips to match responder
            # This ensures both parties converge to the same key value

            return error_index

        else:
            raise RuntimeError(
                f"Unexpected message header in binary search: {message.header}"
            )


def calculate_binary_search_leakage(block_size: int) -> int:
    """Calculate the information leakage from one binary search.

    Parameters
    ----------
    block_size : int
        Size of the block being searched.

    Returns
    -------
    int
        Number of parity bits that will be exchanged.

    Notes
    -----
    Binary search on a block of size k requires ⌈log₂(k)⌉ parity bits.
    From theoretical doc §2.3: "The cost of locating one error in a block
    of size k is ⌈log₂(k)⌉ bits of public disclosure."
    """
    if block_size <= 1:
        return 0
    import math

    return int(math.ceil(math.log2(block_size)))
