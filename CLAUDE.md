# PlaylistBridge — instructions for Claude

CLI that reads a YouTube Music playlist (public URL or pasted page dump) and adds matching tracks to Spotify Liked Songs. See `README.md` for the architecture.

## Layout
- `playlist_bridge/models.py` — platform-agnostic types (`SourceTrack`, `SearchCandidate`, `MatchResult`, `MigrationSummary`). Modules talk only through these.
- `parser/` — YouTube Music input. `spotify_client/` — spotipy wrapper (OAuth, backoff). `matcher/` — scoring. `state/` — checkpoint so re-runs are safe. `cli.py` — entry point.

## Commands (Python >= 3.10, same as CI)
- `pip install -e ".[dev]"`
- `ruff check .` · `mypy playlist_bridge` · `pytest`

## Rules
- New platforms are added as new parser/client modules; do not put platform specifics into `models.py`, `matcher/` or `state/`.
- Tests must not call real YouTube or Spotify; mock the clients.
- Spotify credentials live in `.env` (see `.env.example`); never commit them.
- `build/` is a build artifact, not source.
