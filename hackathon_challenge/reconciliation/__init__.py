"""Reconciliation package initialization.

This package implements the Cascade error reconciliation protocol
for QKD key reconciliation.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_theorethical_aspects.md §2 (Cascade Protocol)
"""

from hackathon_challenge.reconciliation.binary_search import (
    binary_search_initiator,
    binary_search_responder,
    calculate_binary_search_leakage,
)
from hackathon_challenge.reconciliation.cascade import CascadeReconciliator
from hackathon_challenge.reconciliation.history import BacktrackManager, PassHistory
from hackathon_challenge.reconciliation.utils import (
    apply_permutation_to_key,
    compute_optimal_block_size,
    compute_parity,
    inverse_permutation,
    permute_indices,
    split_into_blocks,
)

__all__ = [
    # Main reconciliator
    "CascadeReconciliator",
    # History management
    "PassHistory",
    "BacktrackManager",
    # Binary search
    "binary_search_initiator",
    "binary_search_responder",
    "calculate_binary_search_leakage",
    # Utilities
    "compute_parity",
    "permute_indices",
    "inverse_permutation",
    "compute_optimal_block_size",
    "split_into_blocks",
    "apply_permutation_to_key",
]
