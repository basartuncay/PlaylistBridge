from unittest.mock import MagicMock, patch

import pytest
from spotipy.exceptions import SpotifyException

from playlist_bridge.spotify_client.client import SpotifyClient


def _make_client() -> SpotifyClient:
    """Build a SpotifyClient without running __init__, so no real SpotifyOAuth,
    network call, or on-disk token cache is ever touched in tests.
    """
    client = SpotifyClient.__new__(SpotifyClient)
    client.sp = MagicMock()
    return client


def test_call_with_backoff_retries_after_429_using_retry_after_header():
    client = _make_client()
    rate_limited = SpotifyException(429, -1, "rate limited", headers={"Retry-After": "2"})
    fn = MagicMock(side_effect=[rate_limited, "ok"])

    with patch("playlist_bridge.spotify_client.client.time.sleep") as mock_sleep:
        result = client.call_with_backoff(fn)

    assert result == "ok"
    assert fn.call_count == 2
    mock_sleep.assert_called_once_with(2)


def test_call_with_backoff_uses_default_delay_when_retry_after_missing():
    client = _make_client()
    rate_limited = SpotifyException(429, -1, "rate limited")
    fn = MagicMock(side_effect=[rate_limited, "ok"])

    with patch("playlist_bridge.spotify_client.client.time.sleep") as mock_sleep:
        result = client.call_with_backoff(fn)

    assert result == "ok"
    mock_sleep.assert_called_once_with(30)


def test_call_with_backoff_raises_non_429_errors_immediately():
    client = _make_client()
    server_error = SpotifyException(500, -1, "server error")
    fn = MagicMock(side_effect=server_error)

    with (
        patch("playlist_bridge.spotify_client.client.time.sleep") as mock_sleep,
        pytest.raises(SpotifyException),
    ):
        client.call_with_backoff(fn)

    assert fn.call_count == 1
    mock_sleep.assert_not_called()


def test_search_track_returns_none_when_no_results():
    client = _make_client()
    client.sp.search.return_value = {"tracks": {"items": []}}

    result = client.search_track("Nonexistent Artist", "Nonexistent Song")

    assert result is None


def test_search_track_returns_first_item_when_results_exist():
    client = _make_client()
    track = {"id": "abc123", "name": "Bohemian Rhapsody"}
    client.sp.search.return_value = {"tracks": {"items": [track]}}

    result = client.search_track("Queen", "Bohemian Rhapsody")

    assert result == track


def test_search_track_omits_artist_from_query_when_artist_is_empty():
    client = _make_client()
    client.sp.search.return_value = {"tracks": {"items": []}}

    client.search_track("", "Imagine")

    _, kwargs = client.sp.search.call_args
    assert kwargs["q"] == "track:Imagine"


def test_add_to_liked_songs_calls_spotipy_with_track_id_list():
    client = _make_client()

    client.add_to_liked_songs("abc123")

    client.sp.current_user_saved_tracks_add.assert_called_once_with(tracks=["abc123"])


def test_from_env_raises_when_required_env_var_is_missing(monkeypatch):
    monkeypatch.setattr("playlist_bridge.spotify_client.client.load_dotenv", MagicMock())
    monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIPY_REDIRECT_URI", raising=False)
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "some-id")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

    with pytest.raises(RuntimeError, match="SPOTIPY_CLIENT_SECRET"):
        SpotifyClient.from_env()


def test_from_env_lists_every_missing_variable(monkeypatch):
    monkeypatch.setattr("playlist_bridge.spotify_client.client.load_dotenv", MagicMock())
    monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIPY_REDIRECT_URI", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        SpotifyClient.from_env()

    message = str(exc_info.value)
    assert "SPOTIPY_CLIENT_ID" in message
    assert "SPOTIPY_CLIENT_SECRET" in message
    assert "SPOTIPY_REDIRECT_URI" in message
