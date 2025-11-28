## Technical Design: Extending QKD Implementation

This document specifies the SquidASM-level architecture for the QKD post-processing pipeline. It mirrors the four-step theoretical structure from
`extending_qkd_theorethical_aspects.md` and maps each step to concrete classes, methods, and APIs.

The reference baseline implementation is `squidasm/examples/applications/qkd/example_qkd.py`, which already provides:

- `QkdProgram` base class (entanglement distribution, sifting, basic error sampling).
- `AliceProgram` and `BobProgram` with raw key extraction.
- `ClassicalSocket` implementation in `squidasm/sim/stack/csocket.py`.

All new code should live under `qia-hackathon-2025/hackathon_challenge/` and follow the modular layout:

```python
hackathon_challenge/
├── protocol.py          # Main Alice/Bob programs (extend QkdProgram)
├── reconciliation.py    # CascadeReconciliator + helpers
├── privacy.py           # PrivacyAmplifier + QBER/length helpers
├── auth.py              # AuthenticatedSocket + key buffer
└── verify.py            # KeyVerifier + polynomial hashing
```

Throughout this document, all functions that touch the network are assumed to be **generators** returning
`Generator[EventExpression, None, T]` and must be called with `yield from` from `Program.run()`.

---

## Step 1 – Key Reconciliation and Verification

Step 1 combines the *Cascade* reconciliation protocol with a *universal-hash-based* key verification stage. It extends the
basic `raw_key` pipeline in `example_qkd.py` with two concrete classes:

- `CascadeReconciliator`: interactive information reconciliation over an `AuthenticatedSocket`.
- `KeyVerifier`: polynomial hashing over $GF(2^n)$ to check post-reconciliation equality.

### 1.1 Mapping to Theoretical Framework

Theoretical Step 1 describes:

- Binary Symmetric Channel model and QBER $p$.
- Cascade multi-pass structure (blocks, permutations, backtracking).
- Polynomial hashing as a universal verification primitive.

In SquidASM terms:

- $K_A, K_B$ correspond to the `raw_key` lists produced by `AliceProgram` and `BobProgram` in `example_qkd.py`.
- Each Cascade pass is a pure Python loop with occasional `yield from socket.recv_structured()` / `socket.send_structured()` calls.
- Hash verification uses a helper `KeyVerifier` that exchanges one or two authenticated messages after Cascade.

### 1.2 `CascadeReconciliator` Class Design

`CascadeReconciliator` operates on a local `numpy` bit array and an `AuthenticatedSocket`. It runs entirely in the
classical phase of `Program.run()`.

```python
from dataclasses import dataclass
from typing import Generator, List, Optional, Tuple

import numpy as np
from netqasm.sdk.classical_communication.message import StructuredMessage
from pydynaa import EventExpression

from hackathon_challenge.auth import AuthenticatedSocket


@dataclass
class PassHistory:
    """Stores parity information for backtracking across passes.

    Attributes
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
    """Interactive Cascade implementation using an authenticated classical channel.

    Parameters
    ----------
    socket : AuthenticatedSocket
        Authenticated classical channel to the peer.
    is_alice : bool
        True if this party initiates parities and binary searches.
    key : List[int]
        Local raw key bits (0/1) before reconciliation.
    rng_seed : int
        Shared permutation seed; must match on Alice and Bob.
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
        The caller (typically ``AliceProgram.run`` / ``BobProgram.run``) must
        delegate with ``yield from reconciler.reconcile()``.
        """

        # Sketch: 3–4 passes with increasing block sizes.
        block_size = self._initial_block_size()
        for pass_index in range(3):
            yield from self._run_pass(pass_index, block_size)
            block_size *= 2

        # After all passes, keys should be reconciled with high probability.
        return self._leakage_bits

    def get_key(self) -> List[int]:
        """Return the reconciled key as a Python list of bits."""

        return self._key.tolist()

    def _initial_block_size(self) -> int:
        # Simple heuristic; can be refined using theoretical formulas
        return max(4, len(self._key) // 50)

    def _run_pass(
        self, pass_index: int, block_size: int
    ) -> Generator[EventExpression, None, None]:
        # 1) Apply permutation based on shared RNG seed and pass index
        permuted_indices = self._permute_indices(pass_index)
        # 2) Partition permuted key into blocks
        # 3) Exchange parities and run binary search on mismatches
        #    using StructuredMessage and strict Alice/Bob turn-taking
        #
        # Implementation detail intentionally omitted here; see
        # Section 1.3 for the binary search communication pattern.
        return None

    def _permute_indices(self, pass_index: int) -> np.ndarray:
        rng = np.random.RandomState(self._rng_seed + pass_index)
        indices = np.arange(len(self._key))
        rng.shuffle(indices)
        return indices

    # Additional helpers: _compute_parity, _record_history, backtracking, etc.
```

#### State Management and Backtracking (`PassHistory`)

Backtracking implements the “cascade” effect from the theory document. Implementation-wise:

- For every block parity you send/receive, append a `PassHistory` instance.
- When a bit is flipped in a later pass, recompute affected block parities in earlier passes by scanning `_history` for
  entries whose `indices` include the flipped bit.
- If a previously even block becomes odd, trigger a new `binary_search` on that block.

This design keeps reconciliation state explicit and testable: `_permute_indices`, parity computation, and backtracking
can be unit-tested without running SquidASM.

### 1.3 Binary Search Protocol with `StructuredMessage`

Binary search is implemented as a deterministic request/response protocol over `AuthenticatedSocket`. To avoid deadlock,
only **one side drives** the search; the other responds.

Message headers (`StructuredMessage.header`) should be short, explicit strings, for example:

- `"CASCADE_REQ"` – Bob requests parity of a sub-block from Alice.
- `"CASCADE_PARITY"` – Alice replies with a single-bit parity.
- `"CASCADE_DONE"` – Bob indicates that the error index has been found.

Sketch of the Bob-side primitive:

```python
def _binary_search_bob(
    self, block_indices: List[int]
) -> Generator[EventExpression, None, int]:
    left = 0
    right = len(block_indices)
    while right - left > 1:
        mid = (left + right) // 2
        left_indices = block_indices[left:mid]

        # Request parity of left half from Alice
        req = StructuredMessage("CASCADE_REQ", left_indices)
        self._socket.send_structured(req)
        parity_msg = yield from self._socket.recv_structured()
        assert parity_msg.header == "CASCADE_PARITY"
        left_parity = int(parity_msg.payload)

        # Compare with local parity to decide which half contains the error
        local_left_parity = self._compute_parity(left_indices)
        if local_left_parity != left_parity:
            right = mid
        else:
            left = mid

    error_index = block_indices[left]
    self._key[error_index] ^= 1
    done = StructuredMessage("CASCADE_DONE", error_index)
    self._socket.send_structured(done)
    return error_index
```

Key SquidASM detail: both `recv_structured` calls above must be used as `yield from self._socket.recv_structured()`
from within a generator.

### 1.4 Key Verification (`KeyVerifier`)

After reconciliation, `KeyVerifier` implements the polynomial hashing primitive from Step 1 of the theoretical doc.
It operates purely classically, using the authenticated channel to exchange seeds and tags.

```python
from typing import Sequence


class KeyVerifier:
    """Implements polynomial hashing over GF(2^n) for key equality check."""

    def __init__(self, tag_bits: int = 64) -> None:
        self._tag_bits = tag_bits

    def verify(
        self,
        socket: AuthenticatedSocket,
        key: Sequence[int],
        is_alice: bool,
    ) -> Generator[EventExpression, None, bool]:
        # Sketch only: concrete GF(2^n) math omitted.
        # 1) Alice samples random seed r and sends (r, tag_A).
        # 2) Bob computes tag_B and sends MATCH/MISMATCH.
        # 3) Both sides return True/False.
        return False
```

Input/output behaviour:

- **Input:** local reconciled key bits and an `AuthenticatedSocket`.
- **Output:** `True` iff keys are equal with collision probability bounded by the chosen security parameter.

---

## Step 2 – QBER Estimation and Privacy Amplification

Step 2 quantifies Eve’s information from reconciliation and compresses the verified key using Toeplitz hashing.
Implementation focuses on:

- Extending the baseline `_estimate_error_rate` logic.
- Implementing a `PrivacyAmplifier` that uses `scipy.linalg.toeplitz`.

### 2.1 QBER Estimation Integration

In `example_qkd.py`, `_estimate_error_rate` already samples a subset of same-basis bits and compares outcomes. For the
extended implementation:

- Keep that function unchanged for the quantum-phase sampling.
- Add a new helper in `privacy.py` that combines:
  - `errors_sample`: mismatches from `_estimate_error_rate`.
  - `errors_cascade`: number of flips performed by `CascadeReconciliator` (obtainable from internal counters).

Sketch:

```python
def estimate_qber_from_cascade(
    total_bits: int,
    sample_errors: int,
    cascade_errors: int,
) -> float:
    """Return QBER estimate combining sample and Cascade corrections."""

    return (sample_errors + cascade_errors) / max(1, total_bits)
```

This helper is pure and testable without SquidASM.

### 2.2 `PrivacyAmplifier` and Toeplitz Matrices

`PrivacyAmplifier` performs the Toeplitz multiplication described in the theoretical doc. It is a local computation
and **must not** be a generator.

```python
from typing import List, Sequence

import numpy as np
from scipy.linalg import toeplitz


class PrivacyAmplifier:
    """Toeplitz-matrix-based privacy amplification.

    Methods here never touch the SquidASM network; they operate entirely
    on local numpy arrays over GF(2).
    """

    def amplify(
        self,
        key: Sequence[int],
        seed: Sequence[int],
        new_length: int,
    ) -> List[int]:
        key_arr = np.array(list(key), dtype=np.uint8)
        old_length = key_arr.size
        if len(seed) != old_length + new_length - 1:
            raise ValueError("Invalid seed length for Toeplitz construction")

        col = np.array(seed[:new_length], dtype=np.uint8)
        row = np.array(seed[new_length - 1 :], dtype=np.uint8)
        T = toeplitz(col, row)
        res = (T @ key_arr) % 2
        return res.astype(int).tolist()
```

API behaviour:

- **Input:** reconciled & verified key bits, Toeplitz seed, and desired output length.
- **Output:** final secret key bits.

Security-parameter–driven key length calculation should be implemented in a separate helper, e.g.
`compute_final_key_length(ell_ver, qber, leak_ec, leak_ver, epsilon_sec)` that directly mirrors the formulas from
the theoretical doc.

Seed distribution is part of the protocol layer:

- Alice samples a random seed, sends it over the `AuthenticatedSocket` as a `StructuredMessage("PA_SEED", seed_bits)`.
- Bob reconstructs the same Toeplitz matrix locally using `PrivacyAmplifier`.

---

## Step 3 – Authentication Layer

Step 3 wraps the classical channel with authentication. In SquidASM this is modelled as a **decorator** around
`ClassicalSocket` from `squidasm/squidasm/sim/stack/csocket.py`.

### 3.1 `AuthenticatedSocket` Wrapper

`ClassicalSocket` exposes a small API:

- `send(msg: str) -> None`
- `recv(**kwargs) -> Generator[EventExpression, None, str]`
- `send_int`, `recv_int`, `send_float`, `recv_float`
- `send_structured(msg: StructuredMessage) -> None`
- `recv_structured(**kwargs) -> Generator[EventExpression, None, StructuredMessage]`

`AuthenticatedSocket` mirrors this API but adds HMAC-based authentication on top, treating
`StructuredMessage.payload` as the message body.

```python
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
        payload_bytes = pickle.dumps(msg.payload)
        tag = hmac.new(self._key, payload_bytes, hashlib.sha256).digest()
        envelope = StructuredMessage(msg.header, (msg.payload, tag))
        self._socket.send_structured(envelope)

    def recv_structured(
        self,
        **kwargs,
    ) -> Generator[EventExpression, None, StructuredMessage]:
        envelope = yield from self._socket.recv_structured(**kwargs)
        payload, tag = envelope.payload
        payload_bytes = pickle.dumps(payload)
        expected_tag = hmac.new(self._key, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise SecurityError("Invalid authentication tag")
        return StructuredMessage(envelope.header, payload)

    # Optional: thin wrappers for send/recv of raw strings or ints if needed.
```

Design notes:

- Serialization: `pickle.dumps` is used to match `StructuredMessage` behaviour; callers should avoid unordered
  structures (or use `OrderedDict`) in payloads to keep serialization deterministic.
- Generator delegation: every call to `recv_structured` must be `yield from auth_socket.recv_structured()`.

### 3.2 Integration into `AliceProgram` / `BobProgram`
In `protocol.py`, the extended QKD programs should:

- Declare classical and EPR sockets in `ProgramMeta` as in `example_qkd.py`.
- Immediately wrap the classical socket in `AuthenticatedSocket` at the top of `run()`.

Example sketch for Alice:

```python
from squidasm.sim.stack.program import ProgramContext


def run(self, context: ProgramContext):
    raw_socket = context.csockets[self.PEER]
    auth_socket = AuthenticatedSocket(raw_socket, self._auth_key)

    pairs_info = yield from self._distribute_states(context, True)
    # ALL_MEASURED synchronization as in example_qkd.py

    # From this point on, always use auth_socket
    pairs_info = yield from self._filter_bases(auth_socket, pairs_info, True)
    # ... cascade, verification, privacy amplification ...
```

`_auth_key` can be provided via constructor or configuration and represents the pre-shared Wegman–Carter key
buffer for this run (modelled here via HMAC-SHA256 for simplicity).

---

## Step 4 – Integration Flow and Verification

Step 4 assembles all components into a single `run()` flow for Alice and Bob. The high-level sequence in
`AliceProgram.run` is:

1. EPR-based raw key generation (existing `QkdProgram._distribute_states`).
2. Sifting (`_filter_bases`).
3. Sampling-based error estimation (`_estimate_error_rate`).
4. Cascade reconciliation (`CascadeReconciliator`).
5. Key verification (`KeyVerifier`).
6. QBER + leakage-based final key length calculation.
7. Privacy amplification (`PrivacyAmplifier`).

### 4.1 Example `AliceProgram.run` Sketch

```python
from typing import Any, Dict

from netqasm.sdk.classical_communication.message import StructuredMessage
from squidasm.sim.stack.program import ProgramContext

from hackathon_challenge.auth import AuthenticatedSocket
from hackathon_challenge.privacy import PrivacyAmplifier, estimate_qber_from_cascade
from hackathon_challenge.reconciliation import CascadeReconciliator
from hackathon_challenge.verify import KeyVerifier


def run(self, context: ProgramContext):
    raw_socket = context.csockets[self.PEER]
    auth_socket = AuthenticatedSocket(raw_socket, self._auth_key)

    pairs_info = yield from self._distribute_states(context, True)
    # Synchronize using ALL_MEASURED as in example_qkd.py

    # Classical post-processing
    pairs_info = yield from self._filter_bases(auth_socket, pairs_info, True)
    pairs_info, sample_qber = yield from self._estimate_error_rate(
        auth_socket, pairs_info, self._num_test_bits, True
    )

    raw_key = [
        pair.outcome
        for pair in pairs_info
        if pair.same_basis and not pair.test_outcome
    ]

    reconciler = CascadeReconciliator(auth_socket, True, raw_key, rng_seed=self._cascade_seed)
    leakage = yield from reconciler.reconcile()
    reconciled_key = reconciler.get_key()

    verifier = KeyVerifier()
    verified = yield from verifier.verify(auth_socket, reconciled_key, is_alice=True)
    if not verified:
        raise RuntimeError("Key verification failed")

    total_qber = estimate_qber_from_cascade(
        total_bits=len(reconciled_key),
        sample_errors=int(sample_qber * len(reconciled_key)),
        cascade_errors=leakage,  # or a separate error counter
    )

    final_len = compute_final_key_length(
        ell_ver=len(reconciled_key),
        qber=total_qber,
        leak_ec=leakage,
        leak_ver=self._verification_leak,
        epsilon_sec=self._epsilon_sec,
    )

    # Seed distribution
    seed = self._rng.integers(0, 2, size=len(reconciled_key) + final_len - 1).tolist()
    auth_socket.send_structured(StructuredMessage("PA_SEED", seed))

    amplifier = PrivacyAmplifier()
    final_key = amplifier.amplify(reconciled_key, seed, final_len)

    return {"secret_key": final_key}
```

Bob’s flow mirrors this closely but receives `PA_SEED` and does not initiate certain messages.

### 4.2 Result Structure and `ProgramMeta` Pitfall

- `run()` must return a `Dict[str, Any]` compatible with SquidASM’s `run()` helper. Typical keys: `"secret_key"`,
  `"qber"`, `"leakage"`.
- `ProgramMeta` **must** list all used sockets:
  - Missing entries for `csockets` or `epr_sockets` will raise `KeyError` when accessing `context.csockets[...]` or
    `context.epr_sockets[...]`.

---

## SquidASM-Specific Pitfalls (10+ Examples)

This section lists concrete, recurring issues when extending `example_qkd.py`.

- **Forgotten `yield from` on network calls**: Calling `socket.recv_structured()` without `yield from` returns a
  generator and never blocks on the network.
- **Missing `yield from connection.flush()` after quantum operations**: In `_distribute_states`, quantum operations
  only take effect after `yield from conn.flush()`. Forgetting this can lead to immediate completion and no
  entanglement generation.
- **Accessing measurement futures without casting**: Measurement results are `Future`-like objects; they must be cast
  with `int(m)` before use.
- **Mismatched send/recv patterns**: If both sides call `send_structured` without a matching `recv_structured`, the
  simulation deadlocks. Design clear initiator/responder roles.
- **Reusing non-deterministic payloads in HMAC**: If `dict` instances are used directly in `StructuredMessage.payload`
  on Python < 3.7, key order is not guaranteed, breaking HMAC verification. Use lists or `OrderedDict`.
- **Exceeding `max_qubits` in `ProgramMeta`**: Allocating more qubits than declared raises `AllocError`. Set
  `max_qubits` conservatively above worst-case simultaneous usage.
- **Multiple outstanding EPR requests**: Creating many EPR pairs without flushing or receiving can trigger subtle
  scheduling bugs (see tests around EPR handling in `squidasm/tests`). Always pair `create_keep`/`recv_keep` calls with
  `yield from conn.flush()`.
- **Missing `csockets` / `epr_sockets` entries in `ProgramMeta`**: Accessing a non-declared socket name from
  `context.csockets` or `context.epr_sockets` results in `KeyError` at runtime.
- **Using blocking CPU-heavy code inside generators**: Long-running classical computations (e.g., large Toeplitz
  multiplications) inside a generator will block the event loop. Keep heavy math outside generators where possible.
- **Non-unique `StructuredMessage.header` values**: Reusing the same header for different message types makes debugging
  hard and can cause protocol confusion. Use explicit, stable headers per message type.

---

## Design Patterns and Class Responsibilities

The implementation should explicitly follow a few standard design patterns to keep the protocol extensible.

- **Strategy Pattern (Reconciliation)**: `Reconciliator` interface with concrete strategies:
  - `CascadeReconciliator` (interactive, baseline).
  - Future `LDPCRreconciliator` (non-interactive, syndrome-based).
- **Decorator / Wrapper Pattern (Authentication)**: `AuthenticatedSocket` wraps `ClassicalSocket` and exposes the same
  API while adding HMAC authentication.
- **Dataclass Pattern (Protocol State)**: `PairInfo` in `example_qkd.py`, `PassHistory`, and potential `CascadeBlock`
  / `PairInfo` variants should all be `@dataclass` instances passed between stages.
- **Static Helper Methods (Math Utilities)**: Pure helper functions for parity computation, GF operations, QBER
  formulas, and key length calculations should be module-level or `@staticmethod`s to make them easy to unit test.
- **Factory Pattern (Configuration)**: A small factory (e.g. `build_qkd_protocol(config)`) can select between
  reconciliation strategies (Cascade vs LDPC) and authentication options based on a configuration object.
- **Logging Pattern**: Every main class (`CascadeReconciliator`, `PrivacyAmplifier`, `AuthenticatedSocket`) should
  obtain loggers via `LogManager.get_stack_logger(__name__)` and include simulation time in log messages where useful.

---

## SquidASM API Reference (QKD-Relevant Subset)

This section summarizes the most relevant APIs used by the QKD implementation. For full details, see the main
SquidASM docs under `squidasm/docs/`.

- `ClassicalSocket` (`squidasm/sim/stack/csocket.py`)
  - `send(msg: str) -> None`
  - `recv(**kwargs) -> Generator[EventExpression, None, str]`
  - `send_structured(msg: StructuredMessage) -> None`
  - `recv_structured(**kwargs) -> Generator[EventExpression, None, StructuredMessage]`
- `ProgramContext` (`squidasm/sim/stack/program.py`)
  - `connection`: quantum connection, provides `flush()`.
  - `csockets`: mapping from peer name to `ClassicalSocket`.
  - `epr_sockets`: mapping from peer name to EPR sockets used in `create_keep` / `recv_keep`.
- `ProgramMeta`
  - Declares `name`, `csockets`, `epr_sockets`, and `max_qubits`. Missing or incorrect entries cause runtime errors.
- `StructuredMessage` (`netqasm.sdk.classical_communication.message`)
  - `StructuredMessage(header: str, payload: Any)` – used as the primary container for all protocol messages.
- `EPRSocket` (via `context.epr_sockets`)
  - `create_keep(num_pairs)` and `recv_keep(num_pairs)` allocate entangled pairs; must be followed by
    `yield from connection.flush()`.
- `LogManager`
  - `LogManager.get_stack_logger(__name__)` – returns a logger configured for the simulation stack.
- `run` helper (`squidasm/run/stack/run.py`)
  - `run(config, programs, num_times)` – executes the configured programs and returns per-run result dictionaries.

---

## Testing and Error-Handling Guidelines

- **Unit tests (pure helpers):**
  - Test `_permute_indices`, parity computation, `estimate_qber_from_cascade`, and Toeplitz multiplication using
    plain Python/NumPy without SquidASM.
- **Integration tests (full protocol):**
  - Adapt `squidasm/examples/run_examples.py` or add dedicated tests under `qia-hackathon-2025/hackathon_challenge/` to
    run Alice/Bob programs end-to-end and check that `secret_key` matches on both sides for various `link_noise`.
- **Error handling:**
  - Treat `AllocError` and `TimeoutError` (from SquidASM) as hard failures for a run.
  - Use a custom `SecurityError` for authentication or verification failures; abort the run and log a security alert.
  - For protocol-level inconsistencies (unexpected headers, malformed payloads), raise a clear exception and fail
    fast rather than silently desynchronizing.

