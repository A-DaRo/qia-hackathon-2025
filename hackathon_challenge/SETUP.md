# Setup Guide: QKD Extension Challenge

## Quick Start

This guide helps you get started with the QKD extension implementation.

## Directory Structure Created

```
qia-hackathon-2025/
├── pyproject.toml           # Project configuration (TOP LEVEL)
└── hackathon_challenge/     # Main package
    ├── config.yaml          # Simulation parameters
    ├── network_config.yaml  # 2-node network topology
    ├── README.md            # Package documentation
    ├── SETUP.md             # This file
    ├── STATUS.md            # Implementation status
    ├── .gitignore           # Git ignore patterns
    │
├── core/                    # Core protocol components
│   ├── __init__.py
│   ├── constants.py         # Protocol constants (QBER_THRESHOLD, etc.)
│   ├── base.py             # Dataclasses (CascadeConfig, QKDResult)
│   └── protocol.py         # AliceProgram & BobProgram (TODO)
│
├── auth/                    # Authentication layer
│   ├── __init__.py
│   ├── exceptions.py       # SecurityError, IntegrityError
│   ├── socket.py           # AuthenticatedSocket (TODO)
│   └── wegman_carter.py    # Wegman-Carter primitives (TODO)
│
├── reconciliation/          # Cascade error correction
│   ├── __init__.py
│   ├── history.py          # PassHistory dataclass
│   ├── utils.py            # Parity, permutation helpers (TODO)
│   ├── binary_search.py    # Binary search protocol (TODO)
│   └── cascade.py          # CascadeReconciliator (TODO)
│
├── verification/            # Key verification
│   ├── __init__.py
│   ├── utils.py            # GF(2^n) arithmetic (TODO)
│   ├── polynomial_hash.py  # Polynomial hashing (TODO)
│   └── verifier.py         # KeyVerifier (TODO)
│
├── privacy/                 # Privacy amplification
│   ├── __init__.py
│   ├── entropy.py          # Binary entropy & key length
│   ├── estimation.py       # QBER estimation
│   ├── utils.py            # Toeplitz helpers
│   └── amplifier.py        # PrivacyAmplifier
│
├── utils/                   # Shared utilities
│   ├── __init__.py
│   ├── logging.py          # Logging helpers (TODO)
│   └── math.py             # XOR operations
│
├── scripts/                 # Execution scripts
│   ├── __init__.py
│   ├── run_simulation.py   # Main runner (TODO)
│   └── analyze_results.py  # Analysis (TODO)
│
└── tests/                   # Test suite
    ├── __init__.py
    ├── conftest.py         # Pytest fixtures
    ├── unit/               # Unit tests
    │   ├── test_auth.py
    │   ├── test_cascade.py
    │   ├── test_verification.py
    │   ├── test_privacy.py
    │   └── test_utils.py
    └── integration/        # Integration tests
        ├── test_full_protocol.py
        └── test_error_scenarios.py
```

## Installation

1. **Navigate to the qia-hackathon-2025 directory (where pyproject.toml is):**
   ```bash
   cd qia-hackathon-2025
   ```

2. **Install the package in development mode:**
   ```bash
   pip install -e .
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

## Implementation Order

Follow the phases outlined in `implementation_plan.md`:

### Phase 0: Foundation (DONE ✓)
- ✓ Directory structure created
- ✓ Configuration files (config.yaml, network_config.yaml)
- ✓ Constants defined (core/constants.py)
- ✓ Base dataclasses (core/base.py)

### Phase 1: Authentication Layer
**Start here:** `auth/socket.py`

1. Implement `AuthenticatedSocket.__init__`
2. Implement `AuthenticatedSocket.send_structured`
3. Implement `AuthenticatedSocket.recv_structured`
4. Run tests: `pytest tests/unit/test_auth.py -v`

### Phase 2: Reconciliation
**Start here:** `reconciliation/utils.py`

1. Implement `compute_parity` and `permute_indices`
2. Implement `binary_search.py` (initiator and responder)
3. Implement `CascadeReconciliator` in `cascade.py`
4. Run tests: `pytest tests/unit/test_cascade.py -v`

### Phase 3: Verification
**Start here:** `verification/polynomial_hash.py`

1. Implement GF arithmetic in `utils.py`
2. Implement `compute_polynomial_hash`
3. Implement `KeyVerifier.verify`
4. Run tests: `pytest tests/unit/test_verification.py -v`

### Phase 4: Privacy Amplification
**Start here:** `privacy/` (already partially complete)

1. Complete any missing implementations
2. Run tests: `pytest tests/unit/test_privacy.py -v`

### Phase 5: Protocol Integration
**Start here:** `core/protocol.py`

1. Implement `AliceProgram.run()`
2. Implement `BobProgram.run()`
3. Complete `scripts/run_simulation.py`
4. Run integration tests: `pytest tests/integration/ -v`

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_auth.py -v

# Run with coverage
pytest --cov=hackathon_challenge --cov-report=html

# View coverage report
open htmlcov/index.html  # or xdg-open on Linux
```

## Running Simulations

Once implementation is complete:

```bash
cd hackathon_challenge
python scripts/run_simulation.py
```

## Configuration

Edit `config.yaml` to adjust:
- Number of EPR pairs
- QBER threshold
- Cascade parameters (passes, block size)
- Security parameters

Edit `network_config.yaml` to adjust:
- EPR pair fidelity (controls QBER)
- Number of qubits per node

## Development Guidelines

1. **Follow Numpydoc format** for all docstrings
   - See: `qia-hackathon-2025/docs/coding_guidelines/numpydoc.rst`

2. **Use type hints** everywhere
   - Example: `def func(x: int) -> str:`

3. **Use logging, not print()**
   - `from hackathon_challenge.utils.logging import get_logger`

4. **Remember generator patterns**
   - Network operations: `yield from socket.recv_structured()`
   - Heavy math: Keep outside generators

5. **Test as you go**
   - Write unit tests alongside implementation
   - Aim for 80%+ coverage

## Key References

- **Implementation Plan**: `../challenges/qkd/implementation_plan.md`
- **Theoretical Framework**: `../docs/challenges/qkd/extending_qkd_theorethical_aspects.md`
- **Technical Guide**: `../docs/challenges/qkd/extending_qkd_technical_aspects.md`
- **Baseline Code**: `../../squidasm/examples/applications/qkd/example_qkd.py`

## Common Pitfalls to Avoid

1. Forgetting `yield from` on network calls
2. Missing `connection.flush()` after EPR operations
3. Not casting measurement futures with `int()`
4. Mismatched send/recv patterns (deadlock)
5. Non-deterministic serialization for HMAC
6. Exceeding `max_qubits` in ProgramMeta
7. Missing socket declarations in ProgramMeta
8. Blocking CPU-heavy code inside generators

See `implementation_plan.md` §7 for complete list and solutions.

## Getting Help

1. Consult the implementation plan for detailed phase-by-phase guidance
2. Review the technical document for SquidASM-specific patterns
3. Check the theoretical document for mathematical foundations
4. Look at `example_qkd.py` for baseline implementation patterns

## Next Steps

1. Review `implementation_plan.md` in detail
2. Start with Phase 1 (Authentication Layer)
3. Follow the phased approach to minimize refactoring
4. Test each component before moving to the next phase

Good luck with the implementation! 🚀
