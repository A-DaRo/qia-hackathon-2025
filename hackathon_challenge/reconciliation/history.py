"""PassHistory dataclass for backtracking.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_technical_aspects.md §1.2
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PassHistory:
    """Stores parity information for backtracking across Cascade passes.

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

    Notes
    -----
    Used to implement the "cascade effect" where correcting an error in
    a later pass exposes errors in earlier passes.
    Reference: extending_qkd_theorethical_aspects.md §2.4
    """

    pass_index: int
    block_index: int
    indices: List[int]
    parity: int
