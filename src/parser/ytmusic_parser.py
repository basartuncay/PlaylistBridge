"""Parser for raw text copied (Ctrl+A) from a YouTube Music library or playlist page.

The page dump typically contains header/menu text, the track list itself, and possibly
a trailing "Suggestions" / "Related playlists" section. These functions isolate the
actual track entries and normalize their titles for downstream searching.
"""
from __future__ import annotations

import re

from src.models import SearchCandidate, SourceTrack

# A track entry spans several lines (title, artist/channel, ...) followed by a
# standalone "MM:SS" or "H:MM:SS" duration line, which marks the end of the entry.
_DURATION_LINE_RE = re.compile(r"^\d{1,2}(?::\d{2}){1,2}$")

# Bracketed/parenthesized noise commonly appended to YouTube video titles.
_NOISE_SUFFIX_RE = re.compile(
    r"[\(\[]\s*(?:official\s*)?(?:music\s*)?"
    r"(?:video|audio|lyrics?|lyric\s*video|visualizer|mv|hd|hq)\s*[\)\]]",
    re.IGNORECASE,
)

# Splits a cleaned title on an "Artist - Title" style separator.
_ARTIST_TITLE_SPLIT_RE = re.compile(r"\s[-–—]\s")

# YouTube auto-generates "<Artist> - Topic" channels for official artist content;
# strip that suffix so the channel name can be used as a plausible artist fallback.
_CHANNEL_TOPIC_SUFFIX_RE = re.compile(r"\s*-\s*topic$", re.IGNORECASE)

# Lines that are just a separator between multiple artist names (e.g. rendered as
# their own text node between "Artist1" and "Artist2") rather than a channel name.
_SEPARATOR_LINES = {",", "&", "and"}


def parse_ytmusic_page(text: str) -> list[SourceTrack]:
    """Parse a full YouTube Music page dump into a list of SourceTrack entries.

    Skips everything up to and including the line that mentions both "views" and
    "tracks" (the playlist header), and stops before a "Suggestions" section if one
    is present, so unrelated recommended tracks are not included.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    start = 0
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "views" in lowered and "tracks" in lowered:
            start = index + 1
            break

    tracks: list[SourceTrack] = []
    buffer: list[str] = []
    for line in lines[start:]:
        if line.lower().startswith("suggestions"):
            break

        if _DURATION_LINE_RE.match(line):
            if buffer:
                title = buffer[0]
                artist = _extract_channel_name(buffer[1:])
                duration_seconds = duration_to_seconds(line)
                tracks.append(
                    SourceTrack(
                        title=title,
                        artist=artist,
                        duration_seconds=duration_seconds,
                    )
                )
            buffer = []
        else:
            buffer.append(line)

    return tracks


def _extract_channel_name(lines: list[str]) -> str:
    """Return the first line that isn't just an artist-list separator ("," / "&" / "and")."""
    for line in lines:
        if line.strip().lower() not in _SEPARATOR_LINES:
            return line
    return ""


def clean_title(title: str) -> str:
    """Strip common YouTube noise suffixes like "(Official Video)" or "[Lyrics]" from a title."""
    cleaned = _NOISE_SUFFIX_RE.sub("", title)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -–—").strip()


def duration_to_seconds(duration: str) -> int:
    """Convert a "MM:SS" or "H:MM:SS" duration string into total seconds."""
    seconds = 0
    for part in duration.strip().split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def build_candidates(entry: SourceTrack) -> list[SearchCandidate]:
    """Build an ordered list of (artist, title) search candidates to try for one entry,
    from most to least specific, ending with a title-only fallback.
    """
    cleaned_title = clean_title(entry.title)

    candidates: list[SearchCandidate] = []
    seen: set[tuple[str, str]] = set()

    def add(artist: str, title: str) -> None:
        artist = artist.strip()
        title = title.strip()
        if not title:
            return
        key = (artist.lower(), title.lower())
        if key in seen:
            return
        seen.add(key)
        candidates.append(SearchCandidate(artist=artist, title=title))

    # 1. "Artist - Title" embedded in the title itself is the most reliable split.
    split = _ARTIST_TITLE_SPLIT_RE.split(cleaned_title, maxsplit=1)
    if len(split) == 2:
        add(split[0], split[1])

    # 2. Fall back to the parsed artist/channel field (stripping the auto-generated
    #    "- Topic" suffix YouTube adds to official artist channels).
    channel_artist = _CHANNEL_TOPIC_SUFFIX_RE.sub("", entry.artist).strip()
    add(channel_artist, cleaned_title)

    # 3. Last resort: search by title only.
    add("", cleaned_title)

    return candidates
