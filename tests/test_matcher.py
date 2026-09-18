from src.matcher.track_matcher import (
    SUSPICIOUS_SCORE_THRESHOLD,
    build_match_result,
    score_match,
)
from src.models import SourceTrack


def test_score_match_high_for_identical_title_and_artist():
    source = SourceTrack(title="Bohemian Rhapsody", artist="Queen", duration_seconds=354)
    score = score_match(source, candidate_artist="Queen", candidate_title="Bohemian Rhapsody")
    assert score == 100.0


def test_score_match_low_for_very_different_title_and_artist():
    source = SourceTrack(title="Bohemian Rhapsody", artist="Queen", duration_seconds=354)
    score = score_match(source, candidate_artist="PSY", candidate_title="Gangnam Style")
    assert score < 30.0


def test_score_match_uses_title_only_when_candidate_artist_is_empty():
    source = SourceTrack(title="Imagine", artist="John Lennon", duration_seconds=184)
    score = score_match(source, candidate_artist="", candidate_title="Imagine")
    assert score == 100.0


def test_score_match_uses_title_only_when_source_artist_is_empty():
    source = SourceTrack(title="Imagine", artist="", duration_seconds=184)
    score = score_match(source, candidate_artist="Queen", candidate_title="Imagine")
    assert score == 100.0


def test_score_match_title_only_ignores_artist_mismatch():
    source = SourceTrack(title="Imagine", artist="John Lennon", duration_seconds=184)
    score = score_match(source, candidate_artist="", candidate_title="Imagine")
    assert score == score_match(
        SourceTrack(title="Imagine", artist="Someone Else", duration_seconds=184),
        candidate_artist="",
        candidate_title="Imagine",
    )


def test_build_match_result_not_suspicious_for_close_match():
    source = SourceTrack(title="Bohemian Rhapsody", artist="Queen", duration_seconds=354)
    spotify_track = {
        "id": "3z8h0TU7ReDPLIbEnYhWZb",
        "name": "Bohemian Rhapsody - Remastered 2011",
        "artists": [{"name": "Queen"}],
    }

    result = build_match_result(source, spotify_track)

    assert result.score >= SUSPICIOUS_SCORE_THRESHOLD
    assert result.is_suspicious is False


def test_build_match_result_suspicious_for_unrelated_match():
    source = SourceTrack(title="Bohemian Rhapsody", artist="Queen", duration_seconds=354)
    spotify_track = {
        "id": "4uLU6hMCjMI75M1A2tKUQC",
        "name": "Never Gonna Give You Up",
        "artists": [{"name": "Rick Astley"}],
    }

    result = build_match_result(source, spotify_track)

    assert result.score < SUSPICIOUS_SCORE_THRESHOLD
    assert result.is_suspicious is True


def test_build_match_result_uses_realistic_spotify_track_shape():
    source = SourceTrack(title="Bohemian Rhapsody", artist="Queen", duration_seconds=354)
    spotify_track = {
        "id": "3z8h0TU7ReDPLIbEnYhWZb",
        "name": "Bohemian Rhapsody",
        "album": {"name": "A Night At The Opera", "release_date": "1975-10-31"},
        "artists": [
            {"name": "Queen", "id": "1dfeR4HaWDbWqFHLkxsg1d"},
        ],
        "duration_ms": 354320,
        "external_urls": {"spotify": "https://open.spotify.com/track/3z8h0TU7ReDPLIbEnYhWZb"},
    }

    result = build_match_result(source, spotify_track)

    assert result.track_id == "3z8h0TU7ReDPLIbEnYhWZb"
    assert result.matched_title == "Bohemian Rhapsody"
    assert result.matched_artist == "Queen"
    assert result.score == 100.0
    assert result.is_suspicious is False
