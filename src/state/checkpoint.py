"""Incremental checkpoint state for migration runs.

Unlike a naive "save once at the end" approach, CheckpointStore persists progress to
disk after every N newly processed entries (and can be forced to flush immediately),
so an interrupted run (Ctrl+C, crash, rate-limit death spiral, etc.) never loses
already-completed work.
"""
from __future__ import annotations

from pathlib import Path


class CheckpointStore:
    """Tracks which source entries have already been processed, persisting incrementally."""

    def __init__(self, path: Path, flush_every: int = 5) -> None:
        """Load existing processed-entry state from `path` if it exists, and remember how
        often (in number of newly processed entries) to auto-flush to disk.
        """
        ...

    def is_processed(self, key: str) -> bool:
        """Return whether an entry with this key has already been processed."""
        ...

    def mark_processed(self, key: str, force_flush: bool = False) -> None:
        """Record an entry as processed. Flushes to disk immediately once `flush_every`
        new entries have accumulated since the last flush, or when `force_flush` is True.
        """
        ...

    def flush(self) -> None:
        """Write the current state to disk immediately, regardless of the flush interval."""
        ...

    def __len__(self) -> int:
        """Return the number of entries recorded as processed."""
        ...
