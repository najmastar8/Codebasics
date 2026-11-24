from __future__ import annotations

import argparse

from tubetutor.ingest import IngestionPipeline


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a YouTube transcript and cache it locally."
    )
    parser.add_argument("url", help="YouTube video URL or 11-character video ID")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Fetch the transcript again instead of using the local cache",
    )
    args = parser.parse_args(argv)

    record = IngestionPipeline().ingest(args.url, force_refresh=args.force_refresh)

    print(f"Title: {record.title}")
    print(f"Transcript source: {record.transcript_source}")
    print(f"Transcript quality: {record.transcript_quality}")
    for sentence in record.sentences[:5]:
        print(f"{sentence.start_s}s: {sentence.text}")


if __name__ == "__main__":
    main()
