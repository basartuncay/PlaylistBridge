"""Command-line entry point for PlaylistBridge.

Wires together the parser, matcher, Spotify client, and checkpoint store to migrate a
YouTube Music page dump into Spotify Liked Songs, and prints an end-of-run summary.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.models import MigrationSummary

DEFAULT_INPUT_PATH = Path("ytmusic_paste.txt")
DEFAULT_STATE_PATH = Path("processed_tracks.json")
DEFAULT_SUSPICIOUS_LOG_PATH = Path("suspicious_tracks.txt")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser, including --input and --dry-run."""
    ...


def run_migration(input_path: Path, dry_run: bool) -> MigrationSummary:
    """Run the full YouTube Music -> Spotify migration and return a summary of the results.

    In --dry-run mode, parses and matches tracks but does not call Spotify's
    add-to-library endpoint or write checkpoint state.
    """
    ...


def print_summary(summary: MigrationSummary) -> None:
    """Print the end-of-run report: added / not-found / suspicious counts and the
    average fuzzy match score.
    """
    ...


def main() -> None:
    """CLI entry point: parse arguments and run the migration."""
    ...


if __name__ == "__main__":
    main()
