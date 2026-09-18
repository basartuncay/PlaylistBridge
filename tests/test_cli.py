from unittest.mock import MagicMock, patch

from src.cli import run_migration


def _page(title: str, artist: str, duration: str) -> str:
    """Build a minimal YouTube Music page dump with a single track entry."""
    return f"My Playlist\n1 tracks • 10 views\n\n{title}\n{artist}\n{duration}\n"


def _spotify_track(track_id: str, name: str, artist: str) -> dict:
    return {"id": track_id, "name": name, "artists": [{"name": artist}]}


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_adds_matched_track(mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch):
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", tmp_path / "suspicious.txt")
    input_path = tmp_path / "input.txt"
    input_path.write_text(_page("Imagine", "John Lennon", "3:04"))

    mock_client = mock_spotify_client_cls.from_env.return_value
    mock_client.search_track.return_value = _spotify_track("abc123", "Imagine", "John Lennon")

    mock_checkpoint = mock_checkpoint_cls.return_value
    mock_checkpoint.is_processed.return_value = False

    summary = run_migration(input_path, dry_run=False)

    assert summary.added == 1
    assert summary.not_found == 0
    assert summary.skipped_already_processed == 0
    assert summary.suspicious_match_count == 0
    assert len(summary.match_scores) == 1

    mock_client.add_to_liked_songs.assert_called_once_with("abc123")
    mock_checkpoint.mark_processed.assert_called_once_with("john lennon::imagine")
    mock_checkpoint.flush.assert_called_once()


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_dry_run_never_touches_spotify_or_checkpoint(
    mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", tmp_path / "suspicious.txt")
    input_path = tmp_path / "input.txt"
    input_path.write_text(_page("Imagine", "John Lennon", "3:04"))

    summary = run_migration(input_path, dry_run=True)

    mock_spotify_client_cls.from_env.assert_not_called()
    mock_checkpoint_cls.assert_not_called()
    assert summary.added == 0
    assert summary.not_found == 0
    assert summary.skipped_already_processed == 0


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_skips_already_processed_track(mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch):
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", tmp_path / "suspicious.txt")
    input_path = tmp_path / "input.txt"
    input_path.write_text(_page("Imagine", "John Lennon", "3:04"))

    mock_client = mock_spotify_client_cls.from_env.return_value
    mock_checkpoint = mock_checkpoint_cls.return_value
    mock_checkpoint.is_processed.return_value = True

    summary = run_migration(input_path, dry_run=False)

    assert summary.skipped_already_processed == 1
    assert summary.added == 0
    mock_client.search_track.assert_not_called()
    mock_client.add_to_liked_songs.assert_not_called()
    mock_checkpoint.mark_processed.assert_not_called()


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_counts_not_found_when_no_candidate_matches(
    mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", tmp_path / "suspicious.txt")
    input_path = tmp_path / "input.txt"
    input_path.write_text(_page("Imagine", "John Lennon", "3:04"))

    mock_client = mock_spotify_client_cls.from_env.return_value
    mock_client.search_track.return_value = None

    mock_checkpoint = mock_checkpoint_cls.return_value
    mock_checkpoint.is_processed.return_value = False

    summary = run_migration(input_path, dry_run=False)

    assert summary.not_found == 1
    assert summary.added == 0
    mock_client.add_to_liked_songs.assert_not_called()
    mock_checkpoint.mark_processed.assert_not_called()


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_flags_suspicious_duration(mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch):
    suspicious_log_path = tmp_path / "suspicious.txt"
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", suspicious_log_path)
    input_path = tmp_path / "input.txt"
    # 11:45 = 705 seconds, above the 600s threshold.
    input_path.write_text(_page("Full Album Mix", "Some Channel", "11:45"))

    mock_client = mock_spotify_client_cls.from_env.return_value
    mock_client.search_track.return_value = _spotify_track("abc123", "Full Album Mix", "Some Channel")

    mock_checkpoint = mock_checkpoint_cls.return_value
    mock_checkpoint.is_processed.return_value = False

    summary = run_migration(input_path, dry_run=False)

    assert summary.suspicious_duration_count == 1
    assert suspicious_log_path.exists()
    assert "705s" in suspicious_log_path.read_text()


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_overwrites_suspicious_log_instead_of_appending(
    mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch
):
    suspicious_log_path = tmp_path / "suspicious.txt"
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", suspicious_log_path)
    input_path = tmp_path / "input.txt"
    # 11:45 = 705 seconds, above the 600s threshold.
    input_path.write_text(_page("Full Album Mix", "Some Channel", "11:45"))

    mock_client = mock_spotify_client_cls.from_env.return_value
    mock_client.search_track.return_value = _spotify_track("abc123", "Full Album Mix", "Some Channel")

    mock_checkpoint = mock_checkpoint_cls.return_value
    mock_checkpoint.is_processed.return_value = False

    run_migration(input_path, dry_run=False)
    run_migration(input_path, dry_run=False)

    contents = suspicious_log_path.read_text()
    assert contents.count("705s") == 1


@patch("src.cli.CheckpointStore")
@patch("src.cli.SpotifyClient")
def test_run_migration_flags_suspicious_match_for_low_score(
    mock_spotify_client_cls, mock_checkpoint_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("src.cli.DEFAULT_SUSPICIOUS_LOG_PATH", tmp_path / "suspicious.txt")
    input_path = tmp_path / "input.txt"
    input_path.write_text(_page("Bohemian Rhapsody", "Queen", "5:55"))

    mock_client = mock_spotify_client_cls.from_env.return_value
    mock_client.search_track.return_value = _spotify_track(
        "xyz789", "Never Gonna Give You Up", "Rick Astley"
    )

    mock_checkpoint = mock_checkpoint_cls.return_value
    mock_checkpoint.is_processed.return_value = False

    summary = run_migration(input_path, dry_run=False)

    assert summary.added == 1
    assert summary.suspicious_match_count == 1
    assert summary.match_scores[0] < 60.0
