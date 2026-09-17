"""Thin wrapper around spotipy: OAuth setup, search, saving to Liked Songs, and
automatic backoff on HTTP 429 rate-limit responses.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

DEFAULT_SCOPE = "user-library-read user-library-modify"
DEFAULT_TOKEN_CACHE_PATH = ".spotify_token_cache"


class SpotifyClient:
    """Authenticated Spotify client with built-in rate-limit backoff."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str = DEFAULT_SCOPE,
        cache_path: str | Path = DEFAULT_TOKEN_CACHE_PATH,
    ) -> None:
        """Create an authenticated spotipy.Spotify instance (opens a browser for OAuth
        consent on first run).
        """
        ...

    @classmethod
    def from_env(cls) -> "SpotifyClient":
        """Build a client from SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET /
        SPOTIPY_REDIRECT_URI environment variables (typically loaded from a .env file).
        """
        ...

    def call_with_backoff(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call a spotipy function, automatically sleeping and retrying if it raises an
        HTTP 429 rate-limit error, so the caller never has to handle that case itself.
        """
        ...

    def search_track(self, artist: str, title: str) -> Optional[dict[str, Any]]:
        """Search Spotify for a track by artist and title, returning the top result
        (or None if nothing was found).
        """
        ...

    def add_to_liked_songs(self, track_id: str) -> None:
        """Add a track to the current user's Liked Songs."""
        ...
