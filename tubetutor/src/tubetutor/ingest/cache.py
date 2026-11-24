from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import TranscriptRecord, TranscriptSentence


class TranscriptCache:
    def __init__(self, db_path: str | Path = "data/cache/transcripts.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transcripts (
                    video_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, video_id: str) -> TranscriptRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM transcripts WHERE video_id = ?", (video_id,)
            ).fetchone()
        if not row:
            return None

        payload = json.loads(row[0])
        payload["sentences"] = [
            TranscriptSentence(**sentence) for sentence in payload["sentences"]
        ]
        return TranscriptRecord(**payload)

    def put(self, record: TranscriptRecord) -> None:
        payload = {
            "video_id": record.video_id,
            "sentences": [
                {"text": sentence.text, "start_s": sentence.start_s, "end_s": sentence.end_s}
                for sentence in record.sentences
            ],
            "title": record.title,
            "channel": record.channel,
            "duration": record.duration,
            "upload_date": record.upload_date,
            "description": record.description,
            "chapter_markers": record.chapter_markers,
            "transcript_source": record.transcript_source,
            "transcript_quality": record.transcript_quality,
            "removed_sponsor_segment": record.removed_sponsor_segment,
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO transcripts (video_id, payload)
                VALUES (?, ?)
                ON CONFLICT(video_id) DO UPDATE SET payload=excluded.payload,
                                                    updated_at=CURRENT_TIMESTAMP
                """,
                (record.video_id, json.dumps(payload, ensure_ascii=False)),
            )
