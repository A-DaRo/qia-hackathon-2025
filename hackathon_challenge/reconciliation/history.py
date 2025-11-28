"""PassHistory dataclass and backtracking management.

Reference:
- implementation_plan.md §Phase 2
- extending_qkd_technical_aspects.md §1.2
- extending_qkd_theorethical_aspects.md §2.4
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class PassHistory:
    """Stores parity information for backtracking across Cascade passes.

    Parameters
    ----------
    pass_index : int
        Index of the Cascade pass (0-indexed).
    block_index : int
        Index of the block within the pass.
    indices : List[int]
        Global key indices contained in this block (in original key order).
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

    def contains_index(self, idx: int) -> bool:
        """Check if this block contains a specific key index.

        Parameters
        ----------
        idx : int
            Key index to check.

        Returns
        -------
        bool
            True if idx is in this block's indices.
        """
        return idx in self.indices

    def flip_parity(self) -> None:
        """Flip the stored parity (called when an error in this block is corrected)."""
        self.parity = 1 - self.parity


@dataclass
class BacktrackManager:
    """Manages history records for Cascade backtracking.

    This class tracks all parity exchanges across all passes to enable
    the "cascade effect" - when an error is corrected in a later pass,
    it may expose errors in earlier passes that were hidden by even
    numbers of errors.

    Parameters
    ----------
    num_passes : int
        Total number of Cascade passes to track.

    Attributes
    ----------
    _history : Dict[int, List[PassHistory]]
        Mapping from pass_index to list of PassHistory entries.
    _index_to_blocks : Dict[int, List[Tuple[int, int]]]
        Mapping from key index to list of (pass_index, block_index) tuples.

    Notes
    -----
    Reference: extending_qkd_theorethical_aspects.md §2.4 (Backtracking)
    """

    num_passes: int
    _history: Dict[int, List[PassHistory]] = field(default_factory=dict)
    _index_to_blocks: Dict[int, List[Tuple[int, int]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize history storage for each pass."""
        for i in range(self.num_passes):
            self._history[i] = []

    def record_block(
        self, pass_index: int, block_index: int, indices: List[int], parity: int
    ) -> None:
        """Record parity information for a block.

        Parameters
        ----------
        pass_index : int
            Current pass index.
        block_index : int
            Block index within the pass.
        indices : List[int]
            Key indices in this block (original key coordinates).
        parity : int
            Computed parity for this block.
        """
        entry = PassHistory(
            pass_index=pass_index, block_index=block_index, indices=indices, parity=parity
        )
        self._history[pass_index].append(entry)

        # Update reverse mapping for efficient backtrack lookup
        for idx in indices:
            if idx not in self._index_to_blocks:
                self._index_to_blocks[idx] = []
            self._index_to_blocks[idx].append((pass_index, block_index))

    def find_affected_blocks(
        self, flipped_index: int, current_pass: int
    ) -> List[PassHistory]:
        """Find blocks in earlier passes affected by a bit flip.

        When a bit is corrected at `flipped_index`, all blocks in previous
        passes that contain this index have their parity changed from even
        to odd (or vice versa). If they become odd, they need re-examination.

        Parameters
        ----------
        flipped_index : int
            The key index that was just corrected.
        current_pass : int
            The current pass index (we only look at earlier passes).

        Returns
        -------
        List[PassHistory]
            List of blocks in earlier passes that contain the flipped index.
        """
        affected = []

        if flipped_index not in self._index_to_blocks:
            return affected

        for pass_idx, block_idx in self._index_to_blocks[flipped_index]:
            if pass_idx < current_pass:
                # Find the actual PassHistory entry
                for entry in self._history[pass_idx]:
                    if entry.block_index == block_idx:
                        affected.append(entry)
                        break

        return affected

    def get_blocks_for_pass(self, pass_index: int) -> List[PassHistory]:
        """Get all recorded blocks for a specific pass.

        Parameters
        ----------
        pass_index : int
            Pass index to retrieve.

        Returns
        -------
        List[PassHistory]
            All blocks recorded for this pass.
        """
        return self._history.get(pass_index, [])

    def update_block_parity(
        self, pass_index: int, block_index: int, new_parity: int
    ) -> None:
        """Update the stored parity for a specific block.

        Parameters
        ----------
        pass_index : int
            Pass containing the block.
        block_index : int
            Block to update.
        new_parity : int
            New parity value (0 or 1).
        """
        for entry in self._history[pass_index]:
            if entry.block_index == block_index:
                entry.parity = new_parity
                break

    def clear(self) -> None:
        """Clear all history records."""
        for pass_idx in self._history:
            self._history[pass_idx] = []
        self._index_to_blocks.clear()
