"""Thin wrapper around spotipy: OAuth setup, search, saving to Liked Songs, and
automatic backoff on HTTP 429 rate-limit responses.
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import spotipy
from dotenv import find_dotenv, load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

T = TypeVar("T")

DEFAULT_SCOPE = "user-library-read user-library-modify"
DEFAULT_TOKEN_CACHE_PATH = ".spotify_token_cache"
DEFAULT_RETRY_AFTER_SECONDS = 30

_REQUIRED_ENV_VARS = ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")


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
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=str(cache_path),
            open_browser=True,
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    @classmethod
    def from_env(cls) -> SpotifyClient:
        """Build a client from SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET /
        SPOTIPY_REDIRECT_URI environment variables (typically loaded from a .env file).
        """
        # usecwd: once installed (pipx), the default search starts in site-packages, not here.
        load_dotenv(find_dotenv(usecwd=True))

        values = {name: os.environ.get(name) for name in _REQUIRED_ENV_VARS}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                f"{', '.join(missing)}. Set them directly or in a .env file."
            )

        client_id, client_secret, redirect_uri = (str(values[n]) for n in _REQUIRED_ENV_VARS)
        return cls(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

    def call_with_backoff(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call a spotipy function, automatically sleeping and retrying if it raises an
        HTTP 429 rate-limit error, so the caller never has to handle that case itself.
        """
        while True:
            try:
                return fn(*args, **kwargs)
            except SpotifyException as e:
                if e.http_status != 429:
                    raise
                retry_after = int(e.headers.get("Retry-After", DEFAULT_RETRY_AFTER_SECONDS))
                time.sleep(retry_after)

    def search_track(self, artist: str, title: str) -> dict[str, Any] | None:
        """Search Spotify for a track by artist and title, returning the top result
        (or None if nothing was found).
        """
        query = f"track:{title}" if not artist else f"artist:{artist} track:{title}"
        results = self.call_with_backoff(self.sp.search, q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        return items[0] if items else None

    def add_to_liked_songs(self, track_id: str) -> None:
        """Add a track to the current user's Liked Songs."""
        self.call_with_backoff(self.sp.current_user_saved_tracks_add, tracks=[track_id])
