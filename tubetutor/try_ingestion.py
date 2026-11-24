from __future__ import annotations

from tubetutor.ingest import IngestionPipeline
from tubetutor.ingest.transcript import TranscriptUnavailableError


def main() -> None:
    url = input("Enter a YouTube video URL: ").strip()
    if not url:
        print("Please enter a YouTube video URL.")
        return

    refresh = input("Fetch again instead of using cache? [y/N]: ").strip().lower()

    try:
        record = IngestionPipeline().ingest(
            url,
            force_refresh=refresh in {"y", "yes"},
        )
    except (ValueError, TranscriptUnavailableError) as exc:
        print(f"Could not ingest this video: {exc}")
        return

    print("\nIngestion succeeded")
    print(f"Title: {record.title or '(not available)'}")
    print(f"Video ID: {record.video_id}")
    print(f"Channel: {record.channel or '(not available)'}")
    print(f"Transcript source: {record.transcript_source}")
    print(f"Transcript quality: {record.transcript_quality}")
    print("\nTranscript preview:")
    for sentence in record.sentences[:5]:
        print(f"  {sentence.start_s}s: {sentence.text}")


if __name__ == "__main__":
    main()
