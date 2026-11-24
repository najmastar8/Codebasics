from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, Iterable

from .clean import CaptionFragment, clean_caption_fragments
from .models import TranscriptRecord, TranscriptSentence


class TranscriptUnavailableError(RuntimeError):
    pass


def get_youtube_metadata(video_id: str) -> dict:
    """Get metadata with yt-dlp; media is not downloaded."""
    import yt_dlp

    options = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(f"https://youtu.be/{video_id}", download=False)

    chapters = info.get("chapters") or []
    return {
        "title": info.get("title") or "",
        "channel": info.get("channel") or info.get("uploader") or "",
        "duration": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "description": info.get("description") or "",
        "chapter_markers": [
            {"title": item.get("title", ""), "start_s": item.get("start_time", 0)}
            for item in chapters
        ],
    }


def fetch_youtube_transcript(video_id: str, languages: Iterable[str] | None = None) -> tuple[list[CaptionFragment], str]:
    """Fetch a transcript, preferring manually created captions."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    languages = list(languages or ["en", "en-US", "en-GB"])

    try:
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_manually_created_transcript(languages)
            source = "manual"
        except Exception:
            transcript = transcript_list.find_generated_transcript(languages)
            source = "auto"
        snippets = transcript.fetch()
    except Exception:
        try:
            snippets = api.fetch(video_id, languages=languages)
            source = "manual"
        except Exception as exc:
            raise TranscriptUnavailableError(
                f"No usable YouTube captions found for video {video_id}"
            ) from exc

    fragments = []
    for snippet in snippets:
        fragments.append(
            CaptionFragment(
                text=getattr(snippet, "text", str(snippet)),
                start=float(getattr(snippet, "start", 0.0)),
                duration=float(getattr(snippet, "duration", 0.0)),
            )
        )
    return fragments, source


def transcribe_with_whisper(video_id: str, output_dir: str | Path = "data/cache/audio") -> tuple[list[CaptionFragment], str]:
    """Download audio and transcribe it locally if openai-whisper is available."""
    import yt_dlp

    try:
        import whisper
    except ImportError as exc:
        raise TranscriptUnavailableError(
            "Whisper fallback is unavailable: install openai-whisper or provide an API fallback"
        ) from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / f"%(id)s.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": template,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([f"https://youtu.be/{video_id}"])

    audio_files = [path for path in output_dir.glob(f"{video_id}.*") if path.suffix.lower() != ".json"]
    if not audio_files:
        raise TranscriptUnavailableError("Audio download produced no usable file")

    model = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
    result = model.transcribe(str(audio_files[0]), word_timestamps=False)
    fragments = []
    for segment in result.get("segments", []):
        fragments.append(
            CaptionFragment(
                text=segment.get("text", "").strip(),
                start=float(segment.get("start", 0.0)),
                duration=float(segment.get("end", 0.0)) - float(segment.get("start", 0.0)),
            )
        )
    return fragments, "whisper"


def build_transcript_record(
    video_id: str,
    fragments: list[CaptionFragment],
    source: str,
    metadata: dict | None = None,
) -> TranscriptRecord:
    metadata = metadata or {}
    sentences, removed_sponsor_segment = clean_caption_fragments(fragments)
    quality = "good" if source == "manual" else "fair" if source == "auto" else "fair"

    return TranscriptRecord(
        video_id=video_id,
        sentences=[TranscriptSentence(sentence.text, sentence.start_s, sentence.end_s) for sentence in sentences],
        title=metadata.get("title", ""),
        channel=metadata.get("channel", ""),
        duration=metadata.get("duration"),
        upload_date=metadata.get("upload_date"),
        description=metadata.get("description", ""),
        chapter_markers=metadata.get("chapter_markers", []),
        transcript_source=source,
        transcript_quality=quality,
        removed_sponsor_segment=removed_sponsor_segment,
    )
