"""Shared, platform-agnostic domain models.

Keeping these independent of any single source or target platform is what lets
PlaylistBridge grow beyond YouTube Music -> Spotify later on: any future parser
produces `SourceTrack` objects, and any future client consumes `SearchCandidate`
and produces `MatchResult` objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceTrack:
    """A single track entry parsed from a source platform's page/export."""

    title: str
    artist: str
    duration_seconds: int
    is_suspicious_duration: bool = False

    def key(self) -> str:
        """Return a stable, case-insensitive identity key used for checkpointing."""
        return f"{self.artist.lower()}::{self.title.lower()}"


@dataclass
class SearchCandidate:
    """One (artist, title) pair to try, in order, when searching the target platform."""

    artist: str
    title: str


@dataclass
class MatchResult:
    """The outcome of matching a SourceTrack against a target-platform search result."""

    track_id: str
    matched_artist: str
    matched_title: str
    score: float
    is_suspicious: bool


@dataclass
class MigrationSummary:
    """Aggregate results of a full migration run, used to print the end-of-run report."""

    added: int = 0
    not_found: int = 0
    skipped_already_processed: int = 0
    suspicious_duration_count: int = 0
    suspicious_match_count: int = 0
    match_scores: list[float] = field(default_factory=list)

    @property
    def average_match_score(self) -> float:
        """Mean fuzzy match score across all successful matches (0.0 if there were none)."""
        if not self.match_scores:
            return 0.0
        return sum(self.match_scores) / len(self.match_scores)
