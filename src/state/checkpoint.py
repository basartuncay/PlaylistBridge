"""Incremental checkpoint state for migration runs.

Unlike a naive "save once at the end" approach, CheckpointStore persists progress to
disk after every N newly processed entries (and can be forced to flush immediately),
so an interrupted run (Ctrl+C, crash, rate-limit death spiral, etc.) never loses
already-completed work.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class CheckpointStore:
    """Tracks which source entries have already been processed, persisting incrementally."""

    def __init__(self, path: Path, flush_every: int = 5) -> None:
        """Load existing processed-entry state from `path` if it exists, and remember how
        often (in number of newly processed entries) to auto-flush to disk.
        """
        self.path = Path(path)
        self.flush_every = flush_every
        self._processed: set[str] = self._load()
        self._pending_count = 0

    def _load(self) -> set[str]:
        """Read the processed-key set from disk, tolerating a missing or corrupt file."""
        if not self.path.exists():
            return set()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return set(data.get("processed_keys", []))
        except (json.JSONDecodeError, OSError, AttributeError):
            return set()

    def is_processed(self, key: str) -> bool:
        """Return whether an entry with this key has already been processed."""
        return key in self._processed

    def mark_processed(self, key: str, force_flush: bool = False) -> None:
        """Record an entry as processed. Flushes to disk immediately once `flush_every`
        new entries have accumulated since the last flush, or when `force_flush` is True.
        """
        if key not in self._processed:
            self._processed.add(key)
            self._pending_count += 1

        if force_flush or self._pending_count >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        """Write the current state to disk immediately, regardless of the flush interval."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"processed_keys": sorted(self._processed)}

        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp_path, self.path)
        except BaseException:
            os.unlink(tmp_path)
            raise

        self._pending_count = 0

    def __len__(self) -> int:
        """Return the number of entries recorded as processed."""
        return len(self._processed)
