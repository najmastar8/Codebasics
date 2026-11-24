from __future__ import annotations

from pathlib import Path

from .cache import TranscriptCache
from .models import TranscriptRecord
from .resolve import resolve_video_id
from .transcript import (
    TranscriptUnavailableError,
    build_transcript_record,
    fetch_youtube_transcript,
    get_youtube_metadata,
    transcribe_with_whisper,
)


class IngestionPipeline:
    def __init__(
        self,
        cache: TranscriptCache | None = None,
        use_whisper_fallback: bool = True,
    ) -> None:
        self.cache = cache or TranscriptCache()
        self.use_whisper_fallback = use_whisper_fallback

    def ingest(self, video_url_or_id: str, force_refresh: bool = False) -> TranscriptRecord:
        video_id = resolve_video_id(video_url_or_id)

        if not force_refresh:
            cached = self.cache.get(video_id)
            if cached:
                return cached

        metadata = get_youtube_metadata(video_id)

        try:
            fragments, source = fetch_youtube_transcript(video_id)
        except TranscriptUnavailableError:
            if not self.use_whisper_fallback:
                raise
            fragments, source = transcribe_with_whisper(video_id)

        record = build_transcript_record(video_id, fragments, source, metadata)
        if not record.sentences:
            raise TranscriptUnavailableError(
                f"Could not extract usable transcript text for video {video_id}"
            )

        self.cache.put(record)
        return record
