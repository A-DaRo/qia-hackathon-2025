"""AuthenticatedSocket wrapper for classical communication.

This module implements HMAC-based authentication on top of ClassicalSocket.

Reference:
- implementation_plan.md §Phase 1
- extending_qkd_technical_aspects.md §Step 3.1
"""

import hashlib
import hmac
import pickle
from typing import Generator

from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

# TODO: Import after SquidASM is available
# from squidasm.sim.stack.csocket import ClassicalSocket
# from hackathon_challenge.auth.exceptions import IntegrityError


class AuthenticatedSocket:
    """Wrapper that adds HMAC-SHA256 authentication to ClassicalSocket.

    All recv-methods that block on the network are generators and must be
    used with `yield from` by callers.

    Parameters
    ----------
    socket : ClassicalSocket
        Underlying classical socket.
    key : bytes
        Pre-shared authentication key.

    Notes
    -----
    Uses deterministic serialization to ensure HMAC consistency.
    Critical: Must use `yield from` for all recv operations.
    """

    def __init__(self, socket: "ClassicalSocket", key: bytes) -> None:
        """Initialize authenticated socket."""
        # TODO: Implement initialization
        pass

    def send_structured(self, msg: StructuredMessage) -> None:
        """Send authenticated message.

        Parameters
        ----------
        msg : StructuredMessage
            Message to send with authentication.
        """
        # TODO: Implement authenticated send
        pass

    def recv_structured(
        self, **kwargs
    ) -> Generator[EventExpression, None, StructuredMessage]:
        """Receive and verify authenticated message.

        Parameters
        ----------
        **kwargs
            Additional arguments passed to underlying recv_structured.

        Yields
        ------
        EventExpression
            Network operation events.

        Returns
        -------
        StructuredMessage
            Verified message.

        Raises
        ------
        IntegrityError
            If HMAC verification fails.
        """
        # TODO: Implement authenticated receive
        pass
