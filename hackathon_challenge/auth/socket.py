"""AuthenticatedSocket wrapper for classical communication.

This module implements HMAC-based authentication on top of ClassicalSocket.

Reference:
- implementation_plan.md §Phase 1
- extending_qkd_technical_aspects.md §Step 3.1
"""

import hashlib
import hmac
import pickle
from typing import TYPE_CHECKING, Generator, Protocol

from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

from hackathon_challenge.auth.exceptions import IntegrityError

if TYPE_CHECKING:
    from squidasm.sim.stack.csocket import ClassicalSocket


class ClassicalSocketProtocol(Protocol):
    """Protocol defining the interface for classical sockets."""

    def send_structured(self, msg: StructuredMessage) -> None:
        """Send a structured message."""
        ...

    def recv_structured(
        self, **kwargs
    ) -> Generator[EventExpression, None, StructuredMessage]:
        """Receive a structured message."""
        ...


class AuthenticatedSocket:
    """Wrapper that adds HMAC-SHA256 authentication to ClassicalSocket.

    All recv-methods that block on the network are generators and must be
    used with ``yield from`` by callers.

    Parameters
    ----------
    socket : ClassicalSocket
        Underlying classical socket.
    key : bytes
        Pre-shared authentication key.

    Notes
    -----
    Uses deterministic serialization to ensure HMAC consistency.
    Critical: Must use ``yield from`` for all recv operations.

    The message format adds an HMAC tag to the payload:
    - Original message: StructuredMessage(header, payload)
    - Authenticated message: StructuredMessage(header, (payload, hmac_tag))

    Reference: extending_qkd_technical_aspects.md §3.1
    """

    def __init__(
        self, socket: "ClassicalSocket", key: bytes
    ) -> None:
        """Initialize authenticated socket.

        Parameters
        ----------
        socket : ClassicalSocket
            Underlying classical socket for communication.
        key : bytes
            Pre-shared authentication key for HMAC computation.
        """
        self._socket = socket
        self._key = key

    def _compute_hmac(self, data: bytes) -> bytes:
        """Compute HMAC-SHA256 for the given data.

        Parameters
        ----------
        data : bytes
            Data to authenticate.

        Returns
        -------
        bytes
            HMAC-SHA256 digest.
        """
        return hmac.new(self._key, data, hashlib.sha256).digest()

    def _serialize_payload(self, payload) -> bytes:
        """Serialize payload deterministically for HMAC computation.

        Parameters
        ----------
        payload : Any
            Payload to serialize.

        Returns
        -------
        bytes
            Serialized payload.

        Notes
        -----
        Uses pickle for serialization. Callers should avoid unordered
        structures (dicts with non-deterministic order) in payloads.
        Reference: extending_qkd_technical_aspects.md §3.2 (pitfall)
        """
        return pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)

    def send_structured(self, msg: StructuredMessage) -> None:
        """Send authenticated message.

        Parameters
        ----------
        msg : StructuredMessage
            Message to send with authentication.

        Notes
        -----
        The message payload is wrapped with an HMAC tag:
        original_payload -> (original_payload, hmac_tag)
        """
        # Serialize the original payload
        payload_bytes = self._serialize_payload(msg.payload)

        # Compute HMAC including the header for full authentication
        header_bytes = msg.header.encode("utf-8")
        data_to_sign = header_bytes + payload_bytes
        tag = self._compute_hmac(data_to_sign)

        # Create authenticated envelope
        authenticated_payload = (msg.payload, tag)
        envelope = StructuredMessage(msg.header, authenticated_payload)

        self._socket.send_structured(envelope)

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
            Verified message with original payload.

        Raises
        ------
        IntegrityError
            If HMAC verification fails.
        """
        # Receive the authenticated envelope
        envelope = yield from self._socket.recv_structured(**kwargs)

        # Extract payload and tag
        try:
            payload, received_tag = envelope.payload
        except (TypeError, ValueError) as e:
            raise IntegrityError(
                f"Invalid authenticated message format: {e}"
            ) from e

        # Verify HMAC
        payload_bytes = self._serialize_payload(payload)
        header_bytes = envelope.header.encode("utf-8")
        data_to_verify = header_bytes + payload_bytes
        expected_tag = self._compute_hmac(data_to_verify)

        if not hmac.compare_digest(received_tag, expected_tag):
            raise IntegrityError(
                f"HMAC verification failed for message with header: {envelope.header}"
            )

        # Return the original message (without the tag)
        return StructuredMessage(envelope.header, payload)

    @property
    def socket(self) -> "ClassicalSocket":
        """Return the underlying socket.

        Returns
        -------
        ClassicalSocket
            The wrapped socket instance.
        """
        return self._socket
