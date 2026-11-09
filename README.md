# PlaylistBridge

[![CI](https://github.com/basartuncay/PlaylistBridge/actions/workflows/ci.yml/badge.svg)](https://github.com/basartuncay/PlaylistBridge/actions/workflows/ci.yml)

A command-line tool that reads a YouTube Music playlist — straight from its public
URL, or from a copy-pasted page dump — and adds the matching tracks to Spotify Liked Songs. Built with an
extensible architecture so that other source/target platform pairs can be
added later without touching the core matching or checkpointing logic.

## Architecture

The domain model is deliberately kept platform-agnostic (`src/models.py`):
`SourceTrack`, `SearchCandidate`, `MatchResult`, and `MigrationSummary` don't
know anything about YouTube Music or Spotify specifically. Every other module
only talks to these shared types, not to each other's internals.

- **`parser/ytmusic_playlist.py`** reads a public playlist by URL via
  `ytmusicapi` (no login) and produces the same `SourceTrack` entries.
- **`parser/ytmusic_parser.py`** turns the raw page dump into `SourceTrack`
  entries and builds an ordered list of `SearchCandidate` guesses per entry.
- **`spotify_client/client.py`** wraps `spotipy`: OAuth setup, rate-limit
  backoff, search, and adding to Liked Songs.
- **`matcher/track_matcher.py`** scores a Spotify search hit against the
  source entry and flags low-confidence matches.
- **`state/checkpoint.py`** tracks which entries have already been migrated
  so re-running the tool is safe and cheap.
- **`cli.py`** wires all of the above together and prints an end-of-run
  summary.

## Design Decisions

**Platform-agnostic shared models.** `SourceTrack` and `SearchCandidate` don't
reference YouTube Music by name, and `MatchResult` doesn't reference Spotify.
The parser is the only thing that needs to know about YouTube Music's page
format, and the client is the only thing that needs to know about Spotify's
API shape. Adding, say, an Apple Music target later means writing a new
client module that consumes `SearchCandidate` and produces `MatchResult` — no
changes to the matching or checkpointing logic.

**Incremental checkpoint with atomic writes.** A migration run can touch
hundreds of tracks and take a long time once rate-limit backoff kicks in.
`CheckpointStore` flushes to disk every few entries (not just once at the
end), and each flush writes to a temp file and `os.replace()`s it over the
real file, so a crash or Ctrl+C mid-write never corrupts the checkpoint —
worst case you lose the last few *unflushed* entries, not the whole file.

**Fuzzy matching with suspicious-match flagging.** Spotify's search endpoint
returns its own idea of the best match, which is frequently wrong for
non-official uploads, remixes, or channels named after the artist rather than
the artist's own page. Instead of trusting the top result blindly, every
match is scored against the original entry (title-weighted, since artist
data is sometimes just a channel name) and anything below
`SUSPICIOUS_SCORE_THRESHOLD` is flagged for manual review rather than
silently trusted.

**Dry-run mode.** Because the tool mutates a real Spotify library, `--dry-run`
lets you see exactly what would be searched for — without creating a Spotify
client, without any network calls, and without touching checkpoint state —
before committing to a real run.

## Testing & Lessons Learned

65/65 tests pass (`pytest -v`). Two real bugs were caught during development
and are worth calling out because they weren't obvious from the code alone:

1. **Empty `source.artist` silently tanked otherwise-perfect matches.**
   `score_match` already handled an empty *candidate* artist (the
   title-only search fallback) by scoring on title alone. But when the
   *source* entry's own artist field was empty — which happens whenever
   `build_candidates`'s title-only fallback is what actually finds a hit —
   the fuzzy ratio between `""` and a real artist name scores `0`, dragging
   a 100%-title-match down to ~60% overall. Fixed by falling back to
   title-only scoring whenever *either* side's artist is empty, with a
   regression test (`test_score_match_uses_title_only_when_source_artist_is_empty`).

2. **`suspicious_tracks.txt` was opened in append mode.** Since the
   suspicious-duration check runs before the checkpoint lookup, a track
   that's suspiciously long gets logged on every single run, whether or not
   it was already migrated. Opening the log in `"a"` mode meant every run
   added another copy of the same entries on top of the last run's. Fixed
   by overwriting the file every run instead
   (`test_run_migration_overwrites_suspicious_log_instead_of_appending`
   calls `run_migration` twice and asserts the log contains exactly one
   copy of the entry, not two).

## Setup & Usage

### Install

```bash
pipx install playlist-bridge        # or: pip install playlist-bridge
```

From source (for development): `pip install -e ".[dev]"`.

### Configure Spotify credentials

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   and create an app.
2. Copy its **Client ID** and **Client Secret**.
3. Add a Redirect URI in the app settings that matches what you'll use
   locally, e.g. `http://127.0.0.1:8888/callback`.
4. Create a `.env` file in the folder you'll run the command from (or export the
   variables in your shell) with the three values:

   ```
   SPOTIPY_CLIENT_ID=your-client-id
   SPOTIPY_CLIENT_SECRET=your-client-secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

Each user brings their own Spotify app. That keeps every run inside your own app's
development-mode quota instead of a shared one.

### Pick a source

**Option A: a public playlist URL (recommended).** Copy the playlist's share link from
YouTube Music or YouTube — no YouTube login or copy-paste needed. Private playlists and
your Liked Music aren't reachable this way; use option B for those.

**Option B: a page dump.** Open your YouTube Music playlist or library page in a browser, select all
(Ctrl+A / Cmd+A), copy, and paste the result into `ytmusic_paste.txt` in the
project root (or any path you pass to `--input`).

> **Copy the whole page, not just the track list.** Include the header/menu
> text above the tracks — the parser locates the line mentioning both
> "views" and "tracks" and skips everything up to and including it, so any
> nav/menu text above the tracks is discarded cleanly. If you paste only the
> track list itself, that header line won't be there, and the parser has no
> reliable anchor for where the real entries start.

### Run

```bash
# Report what would happen, without touching Spotify or checkpoint state
playlist-bridge --playlist "https://music.youtube.com/playlist?list=PL..." --dry-run

# Actually migrate
playlist-bridge --playlist "https://music.youtube.com/playlist?list=PL..."

# Or from a page dump
playlist-bridge --input ytmusic_paste.txt
```

The first real run opens a browser window for Spotify OAuth consent. Progress
is checkpointed to `processed_tracks.json`, so an interrupted run can simply
be re-run — already-migrated tracks are skipped. Suspiciously long entries
(over 10 minutes) are written to `suspicious_tracks.txt` for manual review.

### Run the checks

```bash
ruff check . && mypy playlist_bridge && pytest -v
```

### Releasing

Bump `version` in `pyproject.toml`, then push a matching tag (`git tag v0.2.0 && git push --tags`).
`.github/workflows/publish.yml` builds and uploads to PyPI via trusted publishing (no token
stored in the repo); it refuses to publish if the tag and the package version differ.

## Tech Stack

- **Python** 3.10+
- **[spotipy](https://spotipy.readthedocs.io/)** — Spotify Web API client and OAuth
- **[rapidfuzz](https://github.com/rapidfuzz/RapidFuzz)** — fuzzy string matching for track scoring
- **[ytmusicapi](https://github.com/sigma67/ytmusicapi)** — reading public YouTube Music playlists (unofficial API)
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — loading Spotify credentials from `.env`
- **[pytest](https://docs.pytest.org/)** — test suite

## Future Work

The platform-agnostic model design leaves room to grow in a few directions:

* **Private playlists and Liked Music.** Public playlists are read via
  `ytmusicapi` without login; private ones still need the page-dump path.
  `ytmusicapi`'s browser-auth mode could cover them.
* **Reverse migration (Spotify → YouTube Music).** The shared model types
  were designed with this in mind — it would mainly require a YouTube
  Music *write* client alongside the existing Spotify one.
* **Other platforms.** Apple Music, Tidal, and others could be added as
  either a source or a target without touching the core matching or
  checkpointing logic.
