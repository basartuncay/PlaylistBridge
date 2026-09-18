"""Command-line entry point for PlaylistBridge.

Wires together the parser, matcher, Spotify client, and checkpoint store to migrate a
YouTube Music page dump into Spotify Liked Songs, and prints an end-of-run summary.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.matcher.track_matcher import build_match_result
from src.models import MigrationSummary
from src.parser.ytmusic_parser import build_candidates, parse_ytmusic_page
from src.spotify_client.client import SpotifyClient
from src.state.checkpoint import CheckpointStore

DEFAULT_INPUT_PATH = Path("ytmusic_paste.txt")
DEFAULT_STATE_PATH = Path("processed_tracks.json")
DEFAULT_SUSPICIOUS_LOG_PATH = Path("suspicious_tracks.txt")

# A track longer than this is more likely to be a full album/mix mislabeled as a
# single entry than a genuinely long song, and is worth a human's second look.
SUSPICIOUS_DURATION_THRESHOLD_SECONDS = 600


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser, including --input and --dry-run."""
    parser = argparse.ArgumentParser(
        description="Migrate a YouTube Music page dump into Spotify Liked Songs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to the YouTube Music page dump text file (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report what would happen without actually adding anything to Spotify "
            "or writing checkpoint state."
        ),
    )
    return parser


def run_migration(input_path: Path, dry_run: bool) -> MigrationSummary:
    """Run the full YouTube Music -> Spotify migration and return a summary of the results.

    In --dry-run mode, only the input is parsed: no Spotify client or checkpoint store
    is created, nothing is searched for on Spotify, and nothing is added to Liked Songs
    or written to checkpoint state. Instead, the searches that would have been tried
    for each entry are printed.
    """
    entries = parse_ytmusic_page(input_path.read_text(encoding="utf-8"))

    client: SpotifyClient | None = None
    checkpoint: CheckpointStore | None = None
    if not dry_run:
        client = SpotifyClient.from_env()
        checkpoint = CheckpointStore(DEFAULT_STATE_PATH)

    summary = MigrationSummary()
    suspicious_lines: list[str] = []

    for entry in entries:
        if entry.duration_seconds > SUSPICIOUS_DURATION_THRESHOLD_SECONDS:
            summary.suspicious_duration_count += 1
            suspicious_lines.append(
                f"{entry.artist} - {entry.title} ({entry.duration_seconds}s)"
            )

        if not dry_run and checkpoint.is_processed(entry.key()):
            summary.skipped_already_processed += 1
            continue

        found_track = None
        for candidate in build_candidates(entry):
            if dry_run:
                label = (
                    f"{candidate.artist} - {candidate.title}"
                    if candidate.artist
                    else candidate.title
                )
                print(f"Would search for: {label}")
                continue

            found_track = client.search_track(candidate.artist, candidate.title)
            if found_track:
                break

        if dry_run:
            continue

        if found_track is None:
            summary.not_found += 1
            continue

        match_result = build_match_result(entry, found_track)
        client.add_to_liked_songs(match_result.track_id)
        checkpoint.mark_processed(entry.key())

        summary.added += 1
        summary.match_scores.append(match_result.score)
        if match_result.is_suspicious:
            summary.suspicious_match_count += 1

    if not dry_run:
        checkpoint.flush()

    # Overwritten (not appended) on every run: a track that's no longer suspicious,
    # or was already migrated, would otherwise linger here as a stale duplicate.
    with DEFAULT_SUSPICIOUS_LOG_PATH.open("w", encoding="utf-8") as f:
        if suspicious_lines:
            f.write("\n".join(suspicious_lines) + "\n")

    return summary


def print_summary(summary: MigrationSummary) -> None:
    """Print the end-of-run report: added / not-found / suspicious counts and the
    average fuzzy match score.
    """
    print("Migration summary")
    print(f"  Added: {summary.added}")
    print(f"  Not found: {summary.not_found}")
    print(f"  Skipped (already processed): {summary.skipped_already_processed}")
    print(f"  Suspicious duration: {summary.suspicious_duration_count}")
    print(f"  Suspicious match: {summary.suspicious_match_count}")
    print(f"  Average match score: {summary.average_match_score:.1f}")


def main() -> None:
    """CLI entry point: parse arguments and run the migration."""
    parser = build_arg_parser()
    args = parser.parse_args()
    summary = run_migration(args.input, args.dry_run)
    print_summary(summary)


if __name__ == "__main__":
    main()
