"""YouTube ingestion with transcript caching."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class VideoMetadata:
    video_id: str
    title: str = ""
    channel: str = ""
    duration: int = 0
    upload_date: str = ""
    description: str = ""
    chapters: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class IngestionRecord:
    video_id: str
    url: str
    metadata: VideoMetadata
    segments: tuple[TranscriptSegment, ...]
    transcript_source: str
    quality: str


class IngestionPipeline:
    """Resolve YouTube URLs, fetch transcripts, and cache results in SQLite."""

    def __init__(self, cache_dir: str | Path = "data") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.cache_dir / "tube_trainer.sqlite3"
        self._initialize_database()

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestions (
                    video_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    segments_json TEXT NOT NULL,
                    transcript_source TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    @staticmethod
    def resolve_video_id(url: str) -> str:
        """Extract a video ID from common YouTube URL formats."""
        value = url.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
            return value

        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = parsed.netloc.lower().split(":", 1)[0]
        path_parts = [part for part in parsed.path.split("/") if part]

        if host in {"youtu.be", "www.youtu.be"}:
            video_id = path_parts[0] if path_parts else ""
        elif host.endswith("youtube.com"):
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif path_parts and path_parts[0] in {"shorts", "embed", "live", "v"}:
                video_id = path_parts[1] if len(path_parts) > 1 else ""
            else:
                video_id = ""
        else:
            raise ValueError("URL must belong to YouTube")

        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Could not resolve a YouTube video ID")
        return video_id

    def resolve_playlist_video_ids(self, url: str) -> list[str]:
        """Expand a playlist URL using yt-dlp; returns [] for a normal video URL."""
        parsed = urlparse(url if "://" in url else f"https://{url}")
        playlist_id = parse_qs(parsed.query).get("list", [""])[0]
        if not playlist_id:
            return []

        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError("yt-dlp is required to expand playlists") from exc

        options = {"extract_flat": "in_playlist", "quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(options) as downloader:
            result = downloader.extract_info(url, download=False)

        entries = result.get("entries", []) if result else []
        video_ids: list[str] = []
        for entry in entries:
            if not entry:
                continue
            video_id = entry.get("id") or entry.get("display_id")
            if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                video_ids.append(video_id)
        return video_ids

    def _load_cache(self, video_id: str) -> IngestionRecord | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT url, metadata_json, segments_json, transcript_source, quality
                FROM ingestions WHERE video_id = ?
                """,
                (video_id,),
            ).fetchone()
        if not row:
            return None

        metadata_data = json.loads(row[1])
        metadata_data["chapters"] = tuple(metadata_data.get("chapters", ()))
        metadata = VideoMetadata(**metadata_data)
        segments = tuple(TranscriptSegment(**item) for item in json.loads(row[2]))
        return IngestionRecord(video_id, row[0], metadata, segments, row[3], row[4])

    def _save_cache(self, record: IngestionRecord) -> None:
        metadata = asdict(record.metadata)
        metadata["chapters"] = list(record.metadata.chapters)
        segments = [asdict(segment) for segment in record.segments]
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO ingestions
                    (video_id, url, metadata_json, segments_json, transcript_source, quality)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    url = excluded.url,
                    metadata_json = excluded.metadata_json,
                    segments_json = excluded.segments_json,
                    transcript_source = excluded.transcript_source,
                    quality = excluded.quality,
                    ingested_at = CURRENT_TIMESTAMP
                """,
                (
                    record.video_id,
                    record.url,
                    json.dumps(metadata, ensure_ascii=False),
                    json.dumps(segments, ensure_ascii=False),
                    record.transcript_source,
                    record.quality,
                ),
            )

    def ingest(self, url: str, force_refresh: bool = False) -> IngestionRecord:
        video_id = self.resolve_video_id(url)
        if not force_refresh:
            cached = self._load_cache(video_id)
            if cached:
                return cached

        metadata = self._fetch_metadata(url, video_id)
        raw_segments, source = self._fetch_transcript(video_id)
        segments = merge_caption_fragments(raw_segments)
        segments = tuple(remove_nonspoken_segments(segment) for segment in segments)

        quality = "high" if source == "manual" else "medium" if source == "auto" else "low"
        record = IngestionRecord(video_id, url, metadata, segments, source, quality)
        self._save_cache(record)
        return record

    def _fetch_metadata(self, url: str, video_id: str) -> VideoMetadata:
        try:
            import yt_dlp
        except ImportError:
            return VideoMetadata(video_id=video_id)

        options = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)

        chapters = tuple(
            {"title": chapter.get("title", ""), "start_s": float(chapter.get("start_time", 0)), "end_s": float(chapter.get("end_time", 0))}
            for chapter in (info.get("chapters") or [])
        )
        return VideoMetadata(
            video_id=video_id,
            title=info.get("title", ""),
            channel=info.get("channel") or info.get("uploader") or "",
            duration=int(info.get("duration") or 0),
            upload_date=info.get("upload_date", ""),
            description=info.get("description", ""),
            chapters=chapters,
        )

    def _fetch_transcript(self, video_id: str) -> tuple[list[TranscriptSegment], str]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            api = YouTubeTranscriptApi()
            if hasattr(api, "list"):
                transcript_list = api.list(video_id)
                try:
                    fetched = transcript_list.find_manually_created_transcript(["en"])
                    source = "manual"
                except Exception:
                    fetched = transcript_list.find_generated_transcript(["en"])
                    source = "auto"
                snippets = fetched.fetch()
            else:
                snippets = api.get_transcript(video_id, languages=["en"])
                source = "manual" if getattr(snippets, "is_generated", False) is False else "auto"

            segments = []
            for snippet in snippets:
                if isinstance(snippet, dict):
                    text = snippet.get("text", "")
                    start = float(snippet.get("start", 0))
                    duration = float(snippet.get("duration", 0))
                else:
                    text = getattr(snippet, "text", "")
                    start = float(getattr(snippet, "start", 0))
                    duration = float(getattr(snippet, "duration", 0))
                segments.append(TranscriptSegment(text=text.strip(), start_s=start, end_s=start + duration))
            if segments:
                return segments, source
        except Exception:
            pass

        return self._whisper_fallback(video_id)

    def _whisper_fallback(self, video_id: str) -> tuple[list[TranscriptSegment], str]:
        try:
            import whisper
            import yt_dlp
        except ImportError:
            raise RuntimeError(
                "A transcript could not be fetched. Install yt-dlp and openai-whisper "
                "for fallback transcription, or enable captions for this video."
            )

        audio_path = self.cache_dir / f"{video_id}.%(ext)s"
        options = {
            "format": "bestaudio/best",
            "outtmpl": str(audio_path),
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([f"https://youtu.be/{video_id}"])

        downloaded = next(iter(self.cache_dir.glob(f"{video_id}.*")), None)
        if downloaded is None:
            raise RuntimeError("yt-dlp could not download audio for Whisper fallback")

        model = whisper.load_model("base")
        result = model.transcribe(str(downloaded), verbose=False)
        segments = tuple(
            TranscriptSegment(text=item["text"].strip(), start_s=float(item["start"]), end_s=float(item["end"]))
            for item in result.get("segments", [])
        )
        return list(segments), "whisper"


def merge_caption_fragments(segments: Iterable[TranscriptSegment]) -> list[TranscriptSegment]:
    """Merge caption fragments into sentences while preserving timestamps."""
    merged: list[TranscriptSegment] = []
    words: list[str] = []
    start = 0.0
    end = 0.0

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if not words:
            start = segment.start_s
        words.append(text)
        end = segment.end_s
        combined = " ".join(words)
        if re.search(r"[.!?][\"')\]]?$", text) or len(combined) >= 500:
            merged.append(TranscriptSegment(combined, start, end))
            words = []

    if words:
        merged.append(TranscriptSegment(" ".join(words), start, end))
    return merged


SPONSOR_PATTERN = re.compile(
    r"\b(brief sponsor|sponsored by|this (?:episode|video) is sponsored|thanks to .* for sponsoring)\b",
    re.IGNORECASE,
)
FILLER_PATTERN = re.compile(r"^(?:um|uh|you know)[,.]?\s*", re.IGNORECASE)


def remove_nonspoken_segments(segment: TranscriptSegment) -> TranscriptSegment:
    """Remove detectable filler and basic sponsor-marker text."""
    text = FILLER_PATTERN.sub("", segment.text).strip()
    if SPONSOR_PATTERN.search(text):
        text = re.sub(r"[^.!?]*SPONSOR.*", "", text, flags=re.IGNORECASE).strip()
    return TranscriptSegment(text, segment.start_s, segment.end_s)
