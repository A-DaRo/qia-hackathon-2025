from __future__ import annotations

import abc
import logging
from typing import Any, Dict, Generator, List

from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression
from squidasm.run.stack.run import run
from squidasm.sim.stack.common import LogManager
from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
from squidasm.util import create_two_node_network

from hackathon_challenge.auth import AuthenticatedSocket
from hackathon_challenge.privacy import PrivacyAmplifier, estimate_qber_from_cascade
from hackathon_challenge.reconciliation import CascadeReconciliator
from hackathon_challenge.verify import KeyVerifier


class QkdProgram(Program, abc.ABC):
    """Base class for extended QKD programs.

    This mirrors the structure in ``example_qkd.py`` but is kept minimal
    for the hackathon challenge.
    """

    PEER: str
    ALL_MEASURED = "All qubits measured"

    def __init__(self, num_epr: int, num_test_bits: int | None = None) -> None:
        self._num_epr = num_epr
        self._num_test_bits = num_epr // 4 if num_test_bits is None else num_test_bits
        self.logger = LogManager.get_stack_logger(self.__class__.__name__)

    @abc.abstractmethod
    def run(
        self, context: ProgramContext
    ) -> Generator[EventExpression, None, Dict[str, Any]]:  # pragma: no cover - pattern only
        ...


class AliceProgram(QkdProgram):
    PEER = "Bob"

    def __init__(self, num_epr: int, auth_key: bytes) -> None:
        super().__init__(num_epr=num_epr)
        self._auth_key = auth_key

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="alice_extended_qkd",
            csockets=[self.PEER],
            epr_sockets=[self.PEER],
            max_qubits=1,
        )

    def run(
        self, context: ProgramContext
    ) -> Generator[EventExpression, None, Dict[str, Any]]:
        # For the challenge we reuse the existing distribution, sifting and
        # sampling implementation by calling into the example program is left
        # as an exercise. Here we only show how post-processing would be
        # wired on top of an already computed raw key.

        raw_socket = context.csockets[self.PEER]
        auth_socket = AuthenticatedSocket(raw_socket, self._auth_key)

        # Placeholder raw key; in a full implementation this would come
        # from the EPR distribution and sifting phases.
        raw_key: List[int] = [0, 1, 1, 0, 1, 0, 0, 1]
        sample_qber = 0.0

        reconciler = CascadeReconciliator(
            auth_socket,
            is_alice=True,
            key=raw_key,
            rng_seed=42,
        )
        leakage = yield from reconciler.reconcile()
        reconciled_key = reconciler.get_key()

        verifier = KeyVerifier()
        _ = yield from verifier.verify(auth_socket, reconciled_key, is_alice=True)

        total_qber = estimate_qber_from_cascade(
            total_bits=len(reconciled_key),
            sample_errors=int(sample_qber * len(reconciled_key)),
            cascade_errors=0,
        )
        _ = total_qber

        # Simple choice: keep full length for now
        final_len = len(reconciled_key)
        seed = [0] * (len(reconciled_key) + final_len - 1)
        auth_socket.send_structured(StructuredMessage("PA_SEED", seed))

        amplifier = PrivacyAmplifier()
        final_key = amplifier.amplify(reconciled_key, seed, final_len)

        return {"secret_key": final_key}


class BobProgram(QkdProgram):
    PEER = "Alice"

    def __init__(self, num_epr: int, auth_key: bytes) -> None:
        super().__init__(num_epr=num_epr)
        self._auth_key = auth_key

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="bob_extended_qkd",
            csockets=[self.PEER],
            epr_sockets=[self.PEER],
            max_qubits=1,
        )

    def run(
        self, context: ProgramContext
    ) -> Generator[EventExpression, None, Dict[str, Any]]:
        raw_socket = context.csockets[self.PEER]
        auth_socket = AuthenticatedSocket(raw_socket, self._auth_key)

        # Placeholder raw key; in a full implementation this would come
        # from the EPR distribution and sifting phases.
        raw_key: List[int] = [0, 1, 1, 0, 1, 0, 0, 1]

        reconciler = CascadeReconciliator(
            auth_socket,
            is_alice=False,
            key=raw_key,
            rng_seed=42,
        )
        _ = yield from reconciler.reconcile()
        reconciled_key = reconciler.get_key()

        verifier = KeyVerifier()
        _ = yield from verifier.verify(auth_socket, reconciled_key, is_alice=False)

        # Receive PA seed from Alice and run privacy amplification
        seed_msg = yield from auth_socket.recv_structured()
        assert seed_msg.header == "PA_SEED"
        seed = seed_msg.payload

        amplifier = PrivacyAmplifier()
        final_key = amplifier.amplify(reconciled_key, seed, len(reconciled_key))

        return {"secret_key": final_key}


def _demo_run() -> None:
    """Run a tiny demo of the extended programs on a two-node network."""

    cfg = create_two_node_network(node_names=["Alice", "Bob"], link_noise=0.0)
    num_epr = 10
    auth_key = b"demo-shared-auth-key"

    alice_program = AliceProgram(num_epr=num_epr, auth_key=auth_key)
    bob_program = BobProgram(num_epr=num_epr, auth_key=auth_key)

    alice_program.logger.setLevel(logging.ERROR)
    bob_program.logger.setLevel(logging.ERROR)

    alice_results, bob_results = run(
        config=cfg,
        programs={"Alice": alice_program, "Bob": bob_program},
        num_times=1,
    )

    for i, (alice_result, bob_result) in enumerate(zip(alice_results, bob_results)):
        print(f"run {i}:")
        print("alice secret key:", alice_result["secret_key"])
        print("bob   secret key:", bob_result["secret_key"])


if __name__ == "__main__":
    _demo_run()
