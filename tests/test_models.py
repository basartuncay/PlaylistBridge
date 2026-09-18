from src.models import MigrationSummary, SourceTrack


def test_key_is_lowercase_artist_title():
    track = SourceTrack(title="Bohemian Rhapsody", artist="Queen", duration_seconds=354)
    assert track.key() == "queen::bohemian rhapsody"


def test_key_is_case_insensitive():
    lower = SourceTrack(title="bohemian rhapsody", artist="queen", duration_seconds=354)
    mixed = SourceTrack(title="Bohemian Rhapsody", artist="QUEEN", duration_seconds=354)
    assert lower.key() == mixed.key()


def test_average_match_score_empty_list_is_zero():
    summary = MigrationSummary()
    assert summary.average_match_score == 0.0


def test_average_match_score_computes_mean():
    summary = MigrationSummary(match_scores=[80.0, 90.0, 100.0])
    assert summary.average_match_score == 90.0
