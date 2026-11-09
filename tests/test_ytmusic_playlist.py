from unittest.mock import MagicMock

import pytest

from playlist_bridge.models import SourceTrack
from playlist_bridge.parser.ytmusic_playlist import (
    extract_playlist_id,
    fetch_playlist_tracks,
    tracks_from_playlist,
)

PID = "PLvdemdkxPPQD2DtcqeXMjBfw-WHAnPV0U"


@pytest.mark.parametrize(
    "value",
    [
        f"https://music.youtube.com/playlist?list={PID}",
        f"https://www.youtube.com/watch?v=abc123&list={PID}&index=2",
        f"VL{PID}",
        f"  {PID} ",
    ],
)
def test_extract_playlist_id_accepts_urls_and_ids(value):
    assert extract_playlist_id(value) == PID


@pytest.mark.parametrize(
    "value", ["", "https://music.youtube.com/watch?v=abc123", "not a playlist!", "a/b"]
)
def test_extract_playlist_id_rejects_garbage(value):
    with pytest.raises(ValueError):
        extract_playlist_id(value)


def test_tracks_from_playlist_maps_fields_and_skips_unavailable():
    playlist = {
        "tracks": [
            {
                "title": "Salıncak",
                "artists": [{"name": "Mustafa Ceceli"}, {"name": "Nigar Muharrem"}],
                "duration_seconds": 169,
                "isAvailable": True,
            },
            {"title": "Gone", "artists": [{"name": "X"}], "isAvailable": False},
            {"title": "No Artist Or Duration", "artists": None, "duration_seconds": None},
            {"title": "", "artists": []},
        ]
    }

    assert tracks_from_playlist(playlist) == [
        SourceTrack(title="Salıncak", artist="Mustafa Ceceli, Nigar Muharrem", duration_seconds=169),
        SourceTrack(title="No Artist Or Duration", artist="", duration_seconds=0),
    ]


def test_fetch_playlist_tracks_requests_full_playlist():
    yt = MagicMock()
    yt.get_playlist.return_value = {"tracks": []}

    assert fetch_playlist_tracks(f"https://music.youtube.com/playlist?list={PID}", yt=yt) == []
    yt.get_playlist.assert_called_once_with(PID, limit=None)
