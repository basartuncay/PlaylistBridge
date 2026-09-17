"""Fuzzy matching between a parsed source track and a candidate Spotify search result.

Uses rapidfuzz to score how well a Spotify search hit actually matches the original
source entry, and flags low-confidence matches as suspicious instead of blindly
trusting Spotify's top search result.
"""
from __future__ import annotations

from typing import Any

from src.models import MatchResult, SourceTrack

SUSPICIOUS_SCORE_THRESHOLD = 60.0


def score_match(source: SourceTrack, candidate_artist: str, candidate_title: str) -> float:
    """Compute a 0-100 similarity score between the source entry and a Spotify candidate,
    combining fuzzy ratios on both artist and title (not title alone).
    """
    ...


def build_match_result(source: SourceTrack, spotify_track: dict[str, Any]) -> MatchResult:
    """Score a raw Spotify track object against the source entry and package the result,
    flagging it as suspicious when the combined similarity score is below
    SUSPICIOUS_SCORE_THRESHOLD.
    """
    ...
