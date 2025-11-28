# Implementation Plan: Extending QKD Implementation

This document outlines the comprehensive step-by-step implementation plan for the QKD extension challenge. It is designed to minimize refactoring by building foundational components first and integrating them into the final protocol.

**Reference Documents:**
- `extending_qkd_theorethical_aspects.md` - Mathematical foundations and security proofs
- `extending_qkd_technical_aspects.md` - SquidASM-specific implementation details
- `extending_qkd_implementation.md` - Challenge requirements and goals

---

## 1. Project Structure & Conventions

### 1.1 Directory Layout
All new code will reside in `qia-hackathon-2025/hackathon_challenge/`. The structure follows a nested, modular architecture for maximum extensibility and separation of concerns.

```text
qia-hackathon-2025/hackathon_challenge/
├── pyproject.toml           # Project configuration and dependencies
├── config.yaml              # Default simulation configuration
├── network_config.yaml      # Network topology (2-node setup)
├── README.md                # Package documentation
├── __init__.py              # Package initialization
│
├── core/                    # Core QKD protocol components
│   ├── __init__.py
│   ├── protocol.py          # AliceProgram & BobProgram (main integration)
│   ├── base.py              # Base classes and dataclasses (PairInfo, etc.)
│   └── constants.py         # Protocol constants (QBER thresholds, etc.)
│
├── auth/                    # Authentication layer (Step 3)
│   ├── __init__.py
│   ├── socket.py            # AuthenticatedSocket wrapper
│   ├── wegman_carter.py     # Wegman-Carter authentication primitives
│   └── exceptions.py        # SecurityError and auth-related exceptions
│
├── reconciliation/          # Error correction (Step 1)
│   ├── __init__.py
│   ├── cascade.py           # CascadeReconciliator implementation
│   ├── binary_search.py     # Binary search protocol helpers
│   ├── history.py           # PassHistory dataclass and backtracking logic
│   └── utils.py             # Parity computation, permutation helpers
│
├── verification/            # Key verification (Step 1)
│   ├── __init__.py
│   ├── verifier.py          # KeyVerifier class
│   ├── polynomial_hash.py   # GF(2^n) polynomial hashing implementation
│   └── utils.py             # Field arithmetic helpers
│
├── privacy/                 # Privacy amplification (Step 2)
│   ├── __init__.py
│   ├── amplifier.py         # PrivacyAmplifier with Toeplitz hashing
│   ├── estimation.py        # QBER estimation functions
│   ├── entropy.py           # Binary entropy and key length calculations
│   └── utils.py             # Toeplitz matrix helpers
│
├── utils/                   # Shared utilities
│   ├── __init__.py
│   ├── logging.py           # Logging configuration helpers
│   └── math.py              # Common math operations (XOR, GF operations)
│
├── scripts/                 # Execution scripts
│   ├── __init__.py
│   ├── run_simulation.py    # Main simulation runner
│   └── analyze_results.py   # Post-simulation analysis
│
└── tests/                   # Comprehensive test suite
    ├── __init__.py
    ├── conftest.py          # Pytest fixtures and configuration
    │
    ├── unit/                # Unit tests for individual components
    │   ├── __init__.py
    │   ├── test_auth.py
    │   ├── test_cascade.py
    │   ├── test_verification.py
    │   ├── test_privacy.py
    │   └── test_utils.py
    │
    └── integration/         # Integration tests
        ├── __init__.py
        ├── test_full_protocol.py
        └── test_error_scenarios.py
```

### 1.2 Coding Conventions
*   **Docstrings**: Strict **Numpydoc** format for all classes and functions (see `qia-hackathon-2025/docs/coding_guidelines/numpydoc.rst`).
*   **Typing**: Full type hinting (`typing.List`, `typing.Generator`, etc.).
*   **Logging**: Use `LogManager.get_stack_logger(__name__)`. **Never use `print()`**.
*   **Async/Generators**: Network operations must yield `EventExpression`.
    *   Pattern: `yield from socket.recv_structured()`
    *   See **technical doc Section "SquidASM-Specific Pitfalls"** for common errors.
*   **Configuration**: Use `yaml` for simulation parameters (e.g., `config.yaml`).
*   **Error Handling**: Raise specific exceptions (`SecurityError`, `VerificationError`, etc.).
*   **Design Patterns**: Follow OOP principles (SRP, Strategy, Decorator patterns) as outlined in **technical doc Section "Design Patterns"**.

### 1.3 Key Mathematical Concepts (from Theoretical Document)

#### Step 1: Reconciliation & Verification
- **Binary Symmetric Channel Model**: Error rate $p$ (QBER) determines information leakage
- **Cascade Protocol**: Multi-pass parity checking with backtracking (theoretical doc §2.4)
  - Initial block size: $k_1 \approx 0.73/p$ (theoretical optimum)
  - Leakage: $f \cdot n \cdot h(p)$ where $f \approx 1.05-1.2$ is efficiency factor
- **Polynomial Hashing**: Universal hash over $GF(2^n)$ with collision probability $\leq L/q$ (theoretical doc §3.2-3.3)

#### Step 2: Privacy Amplification
- **QBER Estimation**: Combined sampling + Cascade errors (theoretical doc §2.1)
- **Devetak-Winter Formula**: $\ell_{sec} \approx n[1 - h(QBER) - leak_{EC} - leak_{ver}]$ (theoretical doc §3.3)
- **Toeplitz Hashing**: 2-universal hash family, Leftover Hash Lemma guarantees security (theoretical doc §4.2)

#### Step 3: Authentication
- **Wegman-Carter**: Information-theoretic authentication using $\epsilon$-ASU hash families (theoretical doc Step 3 §2.1)
- **Key Consumption**: $L_{tag}$ bits per message for OTP mask (theoretical doc §3.1)

---

## 2. Implementation Phases

### Phase 0: Foundation Setup
**Goal**: Establish project structure, configuration, and shared utilities.

**Reference**: Technical doc introduction, SquidASM API Reference section

#### Tasks:
1.  **Create directory structure** (as outlined in §1.1)
2.  **Configure `pyproject.toml`**:
    *   Dependencies: `squidasm`, `netqasm`, `numpy`, `scipy`, `pyyaml`, `pytest`
    *   Package metadata
3.  **Define `core/constants.py`**:
    ```python
    # Protocol constants
    QBER_THRESHOLD = 0.11  # Shor-Preskill bound (theoretical doc Step 2 §2.2)
    MIN_KEY_LENGTH = 100   # Minimum viable key length
    SECURITY_PARAMETER = 1e-12  # εₛₑc for verification/PA
    ```
4.  **Implement `core/base.py`**:
    *   Extend `PairInfo` dataclass from `example_qkd.py`
    *   Add configuration dataclasses (`CascadeConfig`, `PrivacyConfig`)
5.  **Create `utils/logging.py`**:
    *   Wrapper for `LogManager.get_stack_logger`
6.  **Setup `config.yaml` and `network_config.yaml`**:
    *   2-node network topology (Alice ↔ Bob)
    *   EPR pair generation parameters

---

### Phase 1: Authentication Layer (`auth/`)
**Goal**: Secure the classical channel before implementing protocols that rely on it.

**Reference**: 
- Technical doc §Step 3 (Authentication Layer)
- Theoretical doc Step 3 (Wegman-Carter)

#### Module Structure:
*   `auth/socket.py`: `AuthenticatedSocket` class
*   `auth/wegman_carter.py`: Toeplitz-based authentication primitives
*   `auth/exceptions.py`: `SecurityError`, `IntegrityError`

#### Implementation Details:

1.  **`auth/exceptions.py`**:
    ```python
    class SecurityError(RuntimeError):
        """Raised when authentication or integrity checks fail."""
    
    class IntegrityError(SecurityError):
        """Raised when HMAC verification fails."""
    ```

2.  **`auth/socket.py` - `AuthenticatedSocket`**:
    *   **Reference**: Technical doc §3.1 (complete code skeleton provided)
    *   **Wraps**: `squidasm.sim.stack.csocket.ClassicalSocket`
    *   **Methods**:
        - `send_structured(msg: StructuredMessage) -> None`
        - `recv_structured(**kwargs) -> Generator[EventExpression, None, StructuredMessage]`
    *   **Mechanism**: HMAC-SHA256 signature appended to serialized payload
    *   **Critical**: Use deterministic serialization (OrderedDict or sorted keys)
    *   **Pitfall Warning**: Must use `yield from` for recv operations (technical doc pitfall #1)

3.  **`auth/wegman_carter.py`**:
    *   Implement Toeplitz-based authentication tag generation
    *   **Reference**: Theoretical doc Step 3 §3.1 (Toeplitz hashing for authentication)
    *   Functions:
        - `generate_auth_tag(message: bytes, key: bytes) -> bytes`
        - `verify_auth_tag(message: bytes, tag: bytes, key: bytes) -> bool`

#### Unit Tests (`tests/unit/test_auth.py`):
- Test message integrity (valid signature passes)
- Test tampering detection (invalid signature raises `SecurityError`)
- Test deterministic serialization (same message → same HMAC)

---

### Phase 2: Reconciliation (`reconciliation/`)
**Goal**: Implement the Cascade protocol to correct errors in the raw key.

**Reference**: 
- Technical doc §Step 1 (Key Reconciliation)
- Theoretical doc Step 1 §2 (Cascade Protocol)

#### Module Structure:
*   `reconciliation/history.py`: `PassHistory` dataclass
*   `reconciliation/utils.py`: Parity, permutation helpers
*   `reconciliation/binary_search.py`: Interactive bisection protocol
*   `reconciliation/cascade.py`: `CascadeReconciliator` class

#### Implementation Details:

1.  **`reconciliation/history.py`**:
    ```python
    @dataclass
    class PassHistory:
        """Stores parity info for backtracking (theoretical doc §2.4)."""
        pass_index: int
        block_index: int
        indices: List[int]
        parity: int
    ```

2.  **`reconciliation/utils.py`**:
    *   `compute_parity(key: np.ndarray, indices: List[int]) -> int`
    *   `permute_indices(length: int, seed: int, pass_idx: int) -> np.ndarray`
    *   **Reference**: Technical doc §1.2 (state management)

3.  **`reconciliation/binary_search.py`**:
    *   Implement BINARY primitive (theoretical doc §2.3)
    *   **Protocol messages**:
        - `"CASCADE_REQ"` - Request parity of sub-block
        - `"CASCADE_PARITY"` - Response with parity bit
        - `"CASCADE_DONE"` - Error index found
    *   **Reference**: Technical doc §1.3 (complete protocol sketch)
    *   **Role Definition**: Alice initiates, Bob responds (avoid deadlock)

4.  **`reconciliation/cascade.py` - `CascadeReconciliator`**:
    *   **Reference**: Technical doc §1.2 (complete class skeleton)
    *   **Constructor Parameters**:
        - `socket: AuthenticatedSocket`
        - `is_alice: bool`
        - `key: List[int]`
        - `rng_seed: int`
        - `initial_block_size: Optional[int] = None` (auto-compute from QBER if None)
    *   **Key Methods**:
        - `reconcile() -> Generator[EventExpression, None, int]` (returns leakage bits)
        - `get_key() -> List[int]`
        - `_run_pass(pass_index, block_size) -> Generator[...]`
        - `_backtrack(flipped_index) -> Generator[...]` (theoretical doc §2.4)
    *   **Initial Block Size**: Use $k_1 = \max(4, \lceil 0.73/p \rceil)$ where $p$ is estimated QBER
    *   **Leakage Tracking**: Count every parity bit exchanged (theoretical doc §3.2)

#### Unit Tests (`tests/unit/test_cascade.py`):
- Test `compute_parity` correctness
- Test `permute_indices` determinism (same seed → same permutation)
- Test binary search locates single error
- Mock socket test: full reconciliation with known error pattern

---

### Phase 3: Verification (`verification/`)
**Goal**: Ensure keys are identical after reconciliation using Universal Hashing.

**Reference**:
- Technical doc §1.4 (KeyVerifier)
- Theoretical doc Step 1 §3 (Polynomial Hashing)

#### Module Structure:
*   `verification/utils.py`: GF(2^n) field arithmetic
*   `verification/polynomial_hash.py`: Polynomial evaluation over finite fields
*   `verification/verifier.py`: `KeyVerifier` class

#### Implementation Details:

1.  **`verification/utils.py`**:
    *   Implement GF(2^128) arithmetic (use `numpy` or `galois` library)
    *   Functions for polynomial evaluation

2.  **`verification/polynomial_hash.py`**:
    *   **Mathematical Basis**: Theoretical doc §3.2 (Polynomial Hashing)
    *   **Formula**: $H_r(K) = \sum_{i=1}^{L} m_i r^{L-i+1} \pmod{p}$
    *   `compute_polynomial_hash(key: List[int], salt: int, field_size: int) -> int`

3.  **`verification/verifier.py` - `KeyVerifier`**:
    *   **Reference**: Technical doc §1.4
    *   **Constructor**: `__init__(self, tag_bits: int = 128)`
    *   **Method**: `verify(socket, key, is_alice) -> Generator[EventExpression, None, bool]`
    *   **Protocol**:
        - Alice generates random salt $r \in GF(2^{128})$
        - Alice computes $H_r(K_A)$ and sends `StructuredMessage("VERIFY_HASH", {"salt": r, "tag": H_r(K_A)})`
        - Bob computes $H_r(K_B)$ and compares
        - Return `True` if match, `False` otherwise
    *   **Security**: Collision probability $\leq L/2^{128}$ (theoretical doc §3.3)

#### Unit Tests (`tests/unit/test_verification.py`):
- Test identical keys return `True`
- Test single-bit difference returns `False` with high probability
- Test polynomial hash collision probability bounds

---

### Phase 4: Privacy Amplification & Estimation (`privacy/`)
**Goal**: Estimate information leakage and compress the key.

**Reference**:
- Technical doc §Step 2 (QBER Estimation and Privacy Amplification)
- Theoretical doc Step 2 (Privacy Amplification)

#### Module Structure:
*   `privacy/estimation.py`: QBER estimation functions
*   `privacy/entropy.py`: Binary entropy and key length formulas
*   `privacy/utils.py`: Toeplitz matrix construction
*   `privacy/amplifier.py`: `PrivacyAmplifier` class

#### Implementation Details:

1.  **`privacy/entropy.py`**:
    *   **Reference**: Theoretical doc Step 2 §3.1
    ```python
    def binary_entropy(p: float) -> float:
        """Compute h(p) = -p log₂(p) - (1-p) log₂(1-p)."""
        if p <= 0 or p >= 1:
            return 0.0
        return -p * np.log2(p) - (1 - p) * np.log2(1 - p)
    
    def compute_final_key_length(
        reconciled_length: int,
        qber: float,
        leakage_ec: int,
        leakage_ver: int,
        epsilon_sec: float = 1e-12
    ) -> int:
        """Devetak-Winter formula (theoretical doc §3.3)."""
        security_margin = 2 * np.log2(1 / epsilon_sec)
        available = reconciled_length * (1 - binary_entropy(qber))
        final_length = available - leakage_ec - leakage_ver - security_margin
        return max(0, int(np.floor(final_length)))
    ```

2.  **`privacy/estimation.py`**:
    *   **Reference**: Technical doc §2.1
    ```python
    def estimate_qber_from_cascade(
        total_bits: int,
        sample_errors: int,
        cascade_errors: int,
    ) -> float:
        """Combined QBER estimate (theoretical doc §2.1)."""
        return (sample_errors + cascade_errors) / max(1, total_bits)
    ```

3.  **`privacy/utils.py`**:
    *   Toeplitz matrix construction helpers
    *   **Reference**: Theoretical doc Step 2 §4.2
    ```python
    def generate_toeplitz_seed(key_length: int, final_length: int) -> List[int]:
        """Generate random seed for Toeplitz matrix."""
        seed_length = key_length + final_length - 1
        return [random.randint(0, 1) for _ in range(seed_length)]
    ```

4.  **`privacy/amplifier.py` - `PrivacyAmplifier`**:
    *   **Reference**: Technical doc §2.2 (complete code skeleton)
    *   **Critical**: This is NOT a generator (pure local computation)
    *   **Method**:
    ```python
    def amplify(
        self,
        key: List[int],
        toeplitz_seed: List[int],
        new_length: int,
    ) -> List[int]:
        """Apply Toeplitz hashing (theoretical doc §4.2)."""
        key_arr = np.array(key, dtype=np.uint8)
        # Construct Toeplitz matrix from seed
        col = toeplitz_seed[:len(key)]
        row = toeplitz_seed[len(key)-1:]
        T = toeplitz(col, row)[:new_length, :]
        # Matrix multiplication mod 2
        result = (T @ key_arr) % 2
        return result.astype(int).tolist()
    ```

#### Unit Tests (`tests/unit/test_privacy.py`):
- Test `binary_entropy` against known values
- Test `compute_final_key_length` returns positive values for valid QBER
- Test Toeplitz multiplication dimensions and determinism
- Test QBER estimation formula

---

### Phase 5: Protocol Integration (`core/protocol.py`)
**Goal**: Assemble the full QKD pipeline in SquidASM programs.

**Reference**:
- Technical doc §Step 4 (Integration Flow)
- `squidasm/examples/applications/qkd/example_qkd.py` (baseline implementation)

#### Implementation Details:

1.  **Extend `QkdProgram` from `example_qkd.py`**:
    *   Reuse quantum phase: `_distribute_states`, `_filter_bases`, `_estimate_error_rate`

2.  **`AliceProgram` Structure**:
    *   **Reference**: Technical doc §4.1 (complete run() sketch)
    *   **`ProgramMeta`**: Must declare `csockets` and `epr_sockets` (technical doc §4.2, pitfall #8)
    ```python
    class AliceProgram(QkdProgram):
        PEER = "Bob"
        
        @property
        def meta(self) -> ProgramMeta:
            return ProgramMeta(
                name="alice_qkd",
                csockets=[self.PEER],
                epr_sockets=[self.PEER],
                max_qubits=20,  # Conservative estimate
            )
    ```

3.  **`run()` Method Workflow** (technical doc §4.1):
    ```python
    def run(self, context: ProgramContext):
        # 1. Setup authentication
        raw_socket = context.csockets[self.PEER]
        auth_socket = AuthenticatedSocket(raw_socket, self._auth_key)
        
        # 2. Quantum phase (EPR distribution)
        pairs_info = yield from self._distribute_states(context, is_alice=True)
        # CRITICAL: ALL_MEASURED synchronization (technical pitfall #2)
        yield from context.connection.flush()
        
        # 3. Sifting
        pairs_info = yield from self._filter_bases(auth_socket, pairs_info, is_alice=True)
        
        # 4. Error sampling
        pairs_info, sample_qber = yield from self._estimate_error_rate(
            auth_socket, pairs_info, self._num_test_bits, is_alice=True
        )
        
        # 5. Extract raw key
        raw_key = [pair.outcome for pair in pairs_info 
                   if pair.same_basis and not pair.test_outcome]
        
        # 6. Reconciliation
        reconciler = CascadeReconciliator(
            auth_socket, is_alice=True, key=raw_key, rng_seed=self._cascade_seed
        )
        leakage_ec = yield from reconciler.reconcile()
        reconciled_key = reconciler.get_key()
        
        # 7. Verification
        verifier = KeyVerifier(tag_bits=128)
        is_verified = yield from verifier.verify(auth_socket, reconciled_key, is_alice=True)
        if not is_verified:
            logger.error("Key verification failed. Aborting.")
            return {"error": "verification_failed", "secret_key": []}
        
        # 8. QBER + Final length calculation
        cascade_errors = leakage_ec  # Approximation
        total_qber = estimate_qber_from_cascade(len(raw_key), 0, cascade_errors)
        
        if total_qber > QBER_THRESHOLD:
            logger.error(f"QBER {total_qber:.3f} exceeds threshold. Aborting.")
            return {"error": "qber_too_high", "qber": total_qber, "secret_key": []}
        
        leakage_ver = 128  # Hash tag size
        final_length = compute_final_key_length(
            len(reconciled_key), total_qber, leakage_ec, leakage_ver
        )
        
        # 9. Privacy Amplification
        toeplitz_seed = generate_toeplitz_seed(len(reconciled_key), final_length)
        auth_socket.send_structured(StructuredMessage("PA_SEED", toeplitz_seed))
        
        amplifier = PrivacyAmplifier()
        final_key = amplifier.amplify(reconciled_key, toeplitz_seed, final_length)
        
        return {
            "secret_key": final_key,
            "qber": total_qber,
            "key_length": len(final_key),
            "leakage": leakage_ec + leakage_ver,
        }
    ```

4.  **`BobProgram`**: Mirrors Alice but:
    *   Receives PA seed instead of sending
    *   Responds in binary search instead of initiating
    *   Uses `is_alice=False` in all protocol methods

#### Integration Tests (`tests/integration/test_full_protocol.py`):
- Run full Alice-Bob simulation with low error rate (QBER < 5%)
- Verify keys match after full pipeline
- Test abort on high QBER (> 11%)
- Test error handling (verification failure, key too short)

---

## 3. Configuration & Execution

### 3.1 Configuration File (`config.yaml`)
**Reference**: Technical doc §Step 4.2, SquidASM run API

```yaml
# hackathon_challenge/config.yaml
network:
  path: "network_config.yaml"

simulation:
  num_times: 10  # Run 10 independent sessions
  log_level: "INFO"

programs:
  alice:
    type: "AliceProgram"
    num_epr_pairs: 1000
    num_test_bits: 100
    cascade_seed: 42
    auth_key: "shared_secret_key_alice_bob"
  
  bob:
    type: "BobProgram"
    num_epr_pairs: 1000
    num_test_bits: 100
    cascade_seed: 42
    auth_key: "shared_secret_key_alice_bob"

network_params:
  noise_level: 0.05  # 5% QBER
```

### 3.2 Network Configuration (`network_config.yaml`)

```yaml
# hackathon_challenge/network_config.yaml
nodes:
  - name: "Alice"
    qubits: 20
  - name: "Bob"
    qubits: 20

links:
  - node_1: "Alice"
    node_2: "Bob"
    fidelity: 0.95  # EPR pair fidelity (controls QBER)
```

### 3.3 Execution Script (`scripts/run_simulation.py`)
**Reference**: Technical doc SquidASM API Reference

```python
#!/usr/bin/env python3
"""Run QKD protocol simulation."""

import yaml
from squidasm.run.stack.run import run
from squidasm.util.log import LogManager

from hackathon_challenge.core.protocol import AliceProgram, BobProgram


def main():
    # Load configuration
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Setup logging
    LogManager.set_log_level("INFO")
    logger = LogManager.get_stack_logger(__name__)
    
    # Create program instances
    alice_cfg = config["programs"]["alice"]
    bob_cfg = config["programs"]["bob"]
    
    alice = AliceProgram(
        num_epr_pairs=alice_cfg["num_epr_pairs"],
        num_test_bits=alice_cfg["num_test_bits"],
        cascade_seed=alice_cfg["cascade_seed"],
        auth_key=alice_cfg["auth_key"].encode(),
    )
    
    bob = BobProgram(
        num_epr_pairs=bob_cfg["num_epr_pairs"],
        num_test_bits=bob_cfg["num_test_bits"],
        cascade_seed=bob_cfg["cascade_seed"],
        auth_key=bob_cfg["auth_key"].encode(),
    )
    
    # Run simulation
    logger.info(f"Starting QKD simulation ({config['simulation']['num_times']} runs)...")
    results = run(
        config_file=config["network"]["path"],
        programs={"Alice": alice, "Bob": bob},
        num_times=config["simulation"]["num_times"],
    )
    
    # Analyze results
    success_count = 0
    total_key_length = 0
    
    for i, result in enumerate(results):
        alice_result = result["Alice"]
        bob_result = result["Bob"]
        
        if "error" not in alice_result and "error" not in bob_result:
            if alice_result["secret_key"] == bob_result["secret_key"]:
                success_count += 1
                total_key_length += alice_result["key_length"]
                logger.info(f"Run {i+1}: SUCCESS - Key length: {alice_result['key_length']}, QBER: {alice_result['qber']:.4f}")
            else:
                logger.warning(f"Run {i+1}: FAILED - Keys do not match!")
        else:
            logger.error(f"Run {i+1}: ERROR - {alice_result.get('error', 'unknown')}")
    
    logger.info(f"\n=== Summary ===")
    logger.info(f"Success rate: {success_count}/{len(results)} ({100*success_count/len(results):.1f}%)")
    if success_count > 0:
        logger.info(f"Average key length: {total_key_length/success_count:.1f} bits")


if __name__ == "__main__":
    main()
```

---

## 4. Dependencies & Environment

### 4.1 `pyproject.toml`

```toml
[project]
name = "qkd-extension"
version = "0.1.0"
description = "Extended QKD implementation with Cascade reconciliation and Toeplitz privacy amplification"
requires-python = ">=3.9"

dependencies = [
    "squidasm>=0.11.0",
    "netqasm>=0.14.0",
    "numpy>=1.23.0",
    "scipy>=1.9.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "black>=23.0",
    "flake8>=6.0",
]

[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.black]
line-length = 100
target-version = ['py39']

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 4.2 Installation

```bash
cd qia-hackathon-2025/hackathon_challenge
pip install -e .
pip install -e ".[dev]"  # For development tools
```

---

## 5. Testing Strategy

### 5.1 Unit Tests
**Location**: `tests/unit/`

**Coverage Goals**:
- Authentication: HMAC generation/verification, deterministic serialization
- Reconciliation: Parity computation, permutation, binary search, backtracking logic
- Verification: Polynomial hashing, collision probability
- Privacy: Entropy calculations, Toeplitz matrix operations, QBER estimation

**Run**: `pytest tests/unit/ -v`

### 5.2 Integration Tests
**Location**: `tests/integration/`

**Scenarios**:
- Full protocol with various QBER levels (1%, 5%, 10%)
- Error scenarios (high QBER abort, verification failure)
- Key length calculations under different leakage conditions

**Run**: `pytest tests/integration/ -v`

### 5.3 Coverage Requirements
- Minimum 80% code coverage
- 100% coverage for critical security functions (HMAC, hash verification)

```bash
pytest --cov=hackathon_challenge --cov-report=html
```

---

## 6. Verification Checklist

### Phase 0: Foundation
- [ ] Directory structure created
- [ ] `pyproject.toml` configured with all dependencies
- [ ] Constants defined (`QBER_THRESHOLD`, `SECURITY_PARAMETER`)
- [ ] Base dataclasses implemented
- [ ] Configuration files (`config.yaml`, `network_config.yaml`) created

### Phase 1: Authentication
- [ ] `AuthenticatedSocket` wraps `ClassicalSocket`
- [ ] HMAC-SHA256 signatures generated and verified
- [ ] `SecurityError` raised on tampering
- [ ] Deterministic serialization confirmed
- [ ] Unit tests pass (integrity, tampering detection)

### Phase 2: Reconciliation
- [ ] `PassHistory` dataclass defined
- [ ] Parity computation correct (XOR over indices)
- [ ] Permutation deterministic (same seed → same order)
- [ ] Binary search locates errors correctly
- [ ] `CascadeReconciliator` implements multi-pass structure
- [ ] Backtracking logic revisits previous passes
- [ ] Leakage tracking accurate (counts all parity bits)
- [ ] Unit tests pass (parity, permutation, binary search, full reconciliation)

### Phase 3: Verification
- [ ] GF(2^n) field arithmetic implemented
- [ ] Polynomial hashing computes correct tags
- [ ] `KeyVerifier` exchanges salt and tag correctly
- [ ] Identical keys verify successfully
- [ ] Different keys fail verification with high probability
- [ ] Unit tests pass (hash correctness, collision probability)

### Phase 4: Privacy
- [ ] Binary entropy function correct
- [ ] QBER estimation combines sample + Cascade errors
- [ ] Devetak-Winter formula implemented
- [ ] Final key length calculation accounts for all leakage
- [ ] Toeplitz matrix construction from seed correct
- [ ] `PrivacyAmplifier` performs matrix multiplication mod 2
- [ ] Unit tests pass (entropy, QBER, Toeplitz, key length)

### Phase 5: Integration
- [ ] `AliceProgram` and `BobProgram` extend `QkdProgram`
- [ ] `ProgramMeta` declares all sockets (no `KeyError`)
- [ ] Quantum phase (EPR distribution, sifting) reused from baseline
- [ ] Authentication layer integrated (all messages signed)
- [ ] Full pipeline: quantum → sift → reconcile → verify → amplify
- [ ] QBER threshold check aborts on high error rate
- [ ] Results include `secret_key`, `qber`, `key_length`, `leakage`
- [ ] Alice and Bob keys match in simulation
- [ ] Integration tests pass (full protocol, error scenarios)

### Final Validation
- [ ] Simulation runs to completion without `AllocError` or deadlocks
- [ ] Success rate > 90% for QBER < 8%
- [ ] Final key length > 0 for valid QBER
- [ ] Logs show correct information flow (no `print()` statements)
- [ ] Code coverage ≥ 80%
- [ ] All docstrings follow Numpydoc format
- [ ] Type hints complete (passes `mypy --strict`)

---

## 7. Common Pitfalls & Solutions

**Reference**: Technical doc §"SquidASM-Specific Pitfalls"

1.  **Forgotten `yield from`**: Always use `yield from socket.recv_structured()` for network calls
2.  **Missing `connection.flush()`**: After EPR operations, call `yield from context.connection.flush()`
3.  **Measurement future casting**: Cast measurement results with `int(m)` before use
4.  **Mismatched send/recv**: Design clear initiator/responder roles to avoid deadlock
5.  **Non-deterministic serialization**: Use `OrderedDict` or sorted keys for HMAC payloads
6.  **Exceeding `max_qubits`**: Set `max_qubits` conservatively in `ProgramMeta`
7.  **Multiple EPR requests**: Always flush after `create_keep`/`recv_keep`
8.  **Missing socket declarations**: Declare all sockets in `ProgramMeta.csockets` and `epr_sockets`
9.  **Blocking generators**: Keep CPU-heavy math (Toeplitz) outside generators
10. **Non-unique message headers**: Use explicit headers (`"CASCADE_REQ"`, not `"REQ"`)

---

## 8. Extension Opportunities

After completing the base implementation, consider these enhancements:

1.  **Alternative Reconciliation**: Implement LDPC codes (non-interactive)
2.  **Finite-Key Analysis**: Add statistical security parameters (ν) to QBER estimation
3.  **Key Buffer Management**: Implement Wegman-Carter key consumption tracking
4.  **Performance Optimization**: Parallelize Cascade passes where possible
5.  **Multi-Round Protocol**: Chain multiple QKD sessions to build longer keys
6.  **Configurable Security**: Make $\epsilon_{sec}$ adjustable per-session
7.  **Advanced Verification**: Implement multiple hash families for comparison

---

## 9. References

### Primary Documents
- `extending_qkd_theorethical_aspects.md` - Mathematical foundations
- `extending_qkd_technical_aspects.md` - SquidASM implementation guide
- `extending_qkd_implementation.md` - Challenge requirements

### SquidASM Resources
- `squidasm/examples/applications/qkd/example_qkd.py` - Baseline implementation
- `squidasm/sim/stack/csocket.py` - Classical socket API
- `squidasm/docs/` - API documentation

### Academic Papers (Referenced in Theoretical Doc)
- Brassard & Salvail: "Secret-Key Reconciliation by Public Discussion" (Cascade)
- "Post-processing procedure for industrial quantum key distribution systems" (Toeplitz, Polynomial Hashing)
- Wegman & Carter: Information-theoretic authentication

---

**Document Version**: 1.0  
**Last Updated**: Implementation plan created  
**Status**: Ready for Phase 0 implementation
