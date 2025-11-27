from __future__ import annotations

from typing import Generator, Sequence

from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

from hackathon_challenge.auth import AuthenticatedSocket


class KeyVerifier:
    """Polynomial-hash-based key verification skeleton.

    The concrete finite-field arithmetic is left to the challenge
    participants; this class only defines the communication pattern.
    """

    def __init__(self, tag_bits: int = 64) -> None:
        self._tag_bits = tag_bits

    def verify(
        self,
        socket: AuthenticatedSocket,
        key: Sequence[int],
        is_alice: bool,
    ) -> Generator[EventExpression, None, bool]:
        """Verify that both parties hold the same key.

        Parameters
        ----------
        socket : AuthenticatedSocket
            Authenticated classical channel.
        key : Sequence[int]
            Local reconciled key bits.
        is_alice : bool
            Whether this side initiates the verification.

        Returns
        -------
        bool
            True if verification succeeds, False otherwise.
        """

        # Skeleton protocol:
        # - Alice would generate a random seed and tag, send to Bob.
        # - Bob would recompute the tag and respond with a MATCH/MISMATCH.
        # Here we only exchange a dummy message and always "succeed" to keep
        # the flow runnable without full math.
        if is_alice:
            msg = StructuredMessage("KEY_VERIFY_SEED", {"length": len(key)})
            socket.send_structured(msg)
            reply = yield from socket.recv_structured()
            _ = reply
            return True

        # Bob side
        seed_msg = yield from socket.recv_structured()
        _ = seed_msg
        reply = StructuredMessage("KEY_VERIFY_RESULT", {"match": True})
        socket.send_structured(reply)
        return True
