"""Binary search protocol for error localization.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_theorethical_aspects.md §2.3
"""

from typing import Generator, List

from pydynaa import EventExpression

# TODO: Import after implementation
# from hackathon_challenge.auth.socket import AuthenticatedSocket


def binary_search_initiator(
    socket: "AuthenticatedSocket", block_indices: List[int], key: List[int]
) -> Generator[EventExpression, None, int]:
    """Execute binary search as initiator (Alice).

    Parameters
    ----------
    socket : AuthenticatedSocket
        Authenticated classical channel.
    block_indices : List[int]
        Indices of the block containing an error.
    key : List[int]
        Local key bits.

    Yields
    ------
    EventExpression
        Network operation events.

    Returns
    -------
    int
        Index of the error bit.

    Notes
    -----
    Implements the BINARY primitive from theoretical doc §2.3.
    Cost: ⌈log₂(k)⌉ bits for a block of size k.
    """
    # TODO: Implement binary search (initiator role)
    pass


def binary_search_responder(
    socket: "AuthenticatedSocket", block_indices: List[int], key: List[int]
) -> Generator[EventExpression, None, int]:
    """Execute binary search as responder (Bob).

    Parameters
    ----------
    socket : AuthenticatedSocket
        Authenticated classical channel.
    block_indices : List[int]
        Indices of the block containing an error.
    key : List[int]
        Local key bits.

    Yields
    ------
    EventExpression
        Network operation events.

    Returns
    -------
    int
        Index of the error bit.
    """
    # TODO: Implement binary search (responder role)
    pass
