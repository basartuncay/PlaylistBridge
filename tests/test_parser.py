from playlist_bridge.models import SourceTrack
from playlist_bridge.parser.ytmusic_parser import (
    build_candidates,
    clean_title,
    duration_to_seconds,
    parse_ytmusic_page,
)

SAMPLE_PAGE = """
My Awesome Playlist
120 tracks • 45,392 views

Bohemian Rhapsody (Official Video)
Queen - Topic
5:55
Imagine (Remastered) [Lyrics]
John Lennon
3:04
Perfect Duet
,
Ed Sheeran
&
Beyonce
4:30
Random Video - Full Album Mix
Some Channel
42:10
Suggestions
Recommended Song
Recommended Artist
3:33
"""


def test_parse_ytmusic_page_skips_header_and_returns_tracks():
    tracks = parse_ytmusic_page(SAMPLE_PAGE)

    assert [t.title for t in tracks] == [
        "Bohemian Rhapsody (Official Video)",
        "Imagine (Remastered) [Lyrics]",
        "Perfect Duet",
        "Random Video - Full Album Mix",
    ]
    assert tracks[0].artist == "Queen - Topic"
    assert tracks[0].duration_seconds == 355
    assert tracks[1].artist == "John Lennon"
    assert tracks[1].duration_seconds == 184


def test_parse_ytmusic_page_skips_leading_separator_lines_for_channel_name():
    tracks = parse_ytmusic_page(SAMPLE_PAGE)
    perfect_duet = tracks[2]
    assert perfect_duet.artist == "Ed Sheeran"
    assert perfect_duet.duration_seconds == 270


def test_parse_ytmusic_page_stops_before_suggestions():
    tracks = parse_ytmusic_page(SAMPLE_PAGE)
    assert all(t.title != "Recommended Song" for t in tracks)
    assert len(tracks) == 4


def test_parse_ytmusic_page_never_flags_suspicious_duration():
    tracks = parse_ytmusic_page(SAMPLE_PAGE)
    full_album_mix = tracks[-1]
    assert full_album_mix.duration_seconds == 2530
    assert all(t.is_suspicious_duration is False for t in tracks)


def test_parse_ytmusic_page_without_header_still_parses():
    text = "Some Song\nSome Artist\n3:30\n"
    tracks = parse_ytmusic_page(text)
    assert len(tracks) == 1
    assert tracks[0].title == "Some Song"


def test_parse_ytmusic_page_empty_input_returns_empty_list():
    assert parse_ytmusic_page("") == []


def test_parse_ytmusic_page_artist_empty_when_only_separator_lines_present():
    text = "Some Song\n,\n&\nand\n3:30\n"
    tracks = parse_ytmusic_page(text)
    assert tracks[0].artist == ""


def test_clean_title_strips_official_video_suffix():
    assert clean_title("Bohemian Rhapsody (Official Video)") == "Bohemian Rhapsody"


def test_clean_title_strips_bracketed_lyrics_suffix():
    assert clean_title("Imagine (Remastered) [Lyrics]") == "Imagine (Remastered)"


def test_clean_title_strips_lyric_video_suffix():
    assert clean_title("Someone Like You (Official Lyric Video)") == "Someone Like You"


def test_clean_title_leaves_clean_title_untouched():
    assert clean_title("Hotel California") == "Hotel California"


def test_duration_to_seconds_mm_ss():
    assert duration_to_seconds("3:45") == 225


def test_duration_to_seconds_h_mm_ss():
    assert duration_to_seconds("1:02:03") == 3723


def test_duration_to_seconds_single_digit_minutes():
    assert duration_to_seconds("0:09") == 9


def test_build_candidates_splits_artist_title_from_title():
    entry = SourceTrack(
        title="Queen - Bohemian Rhapsody (Official Video)",
        artist="Queen Official - Topic",
        duration_seconds=355,
    )
    candidates = build_candidates(entry)

    assert candidates[0].artist == "Queen"
    assert candidates[0].title == "Bohemian Rhapsody"


def test_build_candidates_falls_back_to_channel_name_without_topic_suffix():
    entry = SourceTrack(
        title="Imagine (Remastered)",
        artist="John Lennon - Topic",
        duration_seconds=184,
    )
    candidates = build_candidates(entry)

    assert any(c.artist == "John Lennon" and c.title == "Imagine (Remastered)" for c in candidates)


def test_build_candidates_ends_with_title_only_fallback():
    entry = SourceTrack(title="Some Song", artist="Some Channel", duration_seconds=200)
    candidates = build_candidates(entry)

    assert candidates[-1].artist == ""
    assert candidates[-1].title == "Some Song"


def test_build_candidates_deduplicates_identical_candidates():
    entry = SourceTrack(title="Some Song", artist="", duration_seconds=200)
    candidates = build_candidates(entry)

    seen = set()
    for candidate in candidates:
        key = (candidate.artist, candidate.title)
        assert key not in seen
        seen.add(key)
