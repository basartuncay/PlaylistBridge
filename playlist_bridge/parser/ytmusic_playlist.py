"""Read a public YouTube Music / YouTube playlist directly via ytmusicapi (no login).

An alternative source to the page-dump parser: same output type (`SourceTrack`),
so matching, checkpointing and the Spotify side are unchanged.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from playlist_bridge.models import SourceTrack

# YouTube playlist ids: PL..., OLAK5uy_..., RD..., LM etc. Letters, digits, '-' and '_'.
_PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{2,64}$")


def extract_playlist_id(url_or_id: str) -> str:
    """Return the playlist id from a music.youtube.com / youtube.com URL or a bare id.

    Raises:
        ValueError: if no plausible playlist id can be found.
    """
    value = url_or_id.strip()
    if value.startswith(("http://", "https://")):
        candidates = parse_qs(urlparse(value).query).get("list", [])
        value = candidates[0] if candidates else ""
    value = value.removeprefix("VL")
    if not _PLAYLIST_ID_RE.fullmatch(value):
        raise ValueError(f"Not a YouTube playlist URL or id: {url_or_id!r}")
    return value


def tracks_from_playlist(playlist: dict[str, Any]) -> list[SourceTrack]:
    """Convert a ytmusicapi `get_playlist` result into SourceTrack entries.

    Unavailable (deleted/region-blocked) items are skipped; a missing duration becomes 0.
    """
    tracks: list[SourceTrack] = []
    for item in playlist.get("tracks") or []:
        title = (item.get("title") or "").strip()
        if not title or item.get("isAvailable") is False:
            continue
        artists = ", ".join(a["name"] for a in item.get("artists") or [] if a.get("name"))
        tracks.append(
            SourceTrack(
                title=title,
                artist=artists,
                duration_seconds=int(item.get("duration_seconds") or 0),
            )
        )
    return tracks


def fetch_playlist_tracks(url_or_id: str, yt: Any = None) -> list[SourceTrack]:
    """Fetch every track of a public playlist. `yt` is injectable for tests."""
    playlist_id = extract_playlist_id(url_or_id)
    if yt is None:
        from ytmusicapi import YTMusic  # imported lazily: only this source needs it

        yt = YTMusic()
    return tracks_from_playlist(yt.get_playlist(playlist_id, limit=None))
