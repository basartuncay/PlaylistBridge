"""Fuzzy matching between a parsed source track and a candidate Spotify search result.

Uses rapidfuzz to score how well a Spotify search hit actually matches the original
source entry, and flags low-confidence matches as suspicious instead of blindly
trusting Spotify's top search result.
"""
from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from src.models import MatchResult, SourceTrack

SUSPICIOUS_SCORE_THRESHOLD = 60.0

# Title carries more signal than artist: artist is sometimes empty or just a channel
# name (see build_candidates' fallbacks), while the title is usually intact.
TITLE_WEIGHT = 0.6
ARTIST_WEIGHT = 0.4


def score_match(source: SourceTrack, candidate_artist: str, candidate_title: str) -> float:
    """Compute a 0-100 similarity score between the source entry and a Spotify candidate,
    combining fuzzy ratios on both artist and title (not title alone).
    """
    title_score = fuzz.token_sort_ratio(source.title, candidate_title)

    if not candidate_artist.strip() or not source.artist.strip():
        return title_score

    artist_score = fuzz.token_sort_ratio(source.artist, candidate_artist)
    return TITLE_WEIGHT * title_score + ARTIST_WEIGHT * artist_score


def build_match_result(source: SourceTrack, spotify_track: dict[str, Any]) -> MatchResult:
    """Score a raw Spotify track object against the source entry and package the result,
    flagging it as suspicious when the combined similarity score is below
    SUSPICIOUS_SCORE_THRESHOLD.
    """
    matched_title = spotify_track["name"]
    matched_artist = spotify_track["artists"][0]["name"]

    score = score_match(source, matched_artist, matched_title)

    return MatchResult(
        track_id=spotify_track["id"],
        matched_artist=matched_artist,
        matched_title=matched_title,
        score=score,
        is_suspicious=score < SUSPICIOUS_SCORE_THRESHOLD,
    )
