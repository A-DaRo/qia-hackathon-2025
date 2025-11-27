from __future__ import annotations

import hashlib
import hmac
import pickle
from typing import Generator

from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression
from squidasm.sim.stack.csocket import ClassicalSocket


class SecurityError(RuntimeError):
    """Raised when authentication or integrity checks fail."""


class AuthenticatedSocket:
    """Wrapper that adds HMAC-SHA256 authentication to ClassicalSocket.

    All recv-methods that block on the network are generators and must be
    used with ``yield from`` by callers.
    """

    def __init__(self, socket: ClassicalSocket, key: bytes) -> None:
        self._socket = socket
        self._key = key

    def send_structured(self, msg: StructuredMessage) -> None:
        """Send an authenticated structured message.

        Parameters
        ----------
        msg : StructuredMessage
            Message to send.
        """

        payload_bytes = pickle.dumps(msg.payload)
        tag = hmac.new(self._key, payload_bytes, hashlib.sha256).digest()
        envelope = StructuredMessage(msg.header, (msg.payload, tag))
        self._socket.send_structured(envelope)

    def recv_structured(
        self,
        **kwargs,
    ) -> Generator[EventExpression, None, StructuredMessage]:
        """Receive and verify an authenticated structured message.

        Parameters
        ----------
        **kwargs
            Forwarded to the underlying ``ClassicalSocket.recv_structured``.

        Returns
        -------
        StructuredMessage
            The verified message with the original payload.

        Raises
        ------
        SecurityError
            If the authentication tag does not verify.
        """

        envelope = yield from self._socket.recv_structured(**kwargs)
        payload, tag = envelope.payload
        payload_bytes = pickle.dumps(payload)
        expected_tag = hmac.new(self._key, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise SecurityError("Invalid authentication tag")
        return StructuredMessage(envelope.header, payload)
