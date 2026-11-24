from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TranscriptSentence:
    text: str
    start_s: int
    end_s: int


@dataclass
class TranscriptRecord:
    video_id: str
    sentences: list[TranscriptSentence]
    title: str = ""
    channel: str = ""
    duration: int | None = None
    upload_date: str | None = None
    description: str = ""
    chapter_markers: list[dict[str, object]] = field(default_factory=list)
    transcript_source: str = "manual"
    transcript_quality: str = "good"
    removed_sponsor_segment: bool = False
