"""Lightweight local tracing for YouTube Recipe Writer requests."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path


class TraceStore:
    def __init__(self, cache_dir: str | Path = "data") -> None:
        self.database_path = Path(cache_dir) / "tube_trainer.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    request TEXT NOT NULL,
                    video_ids TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    retrieved_chunks TEXT NOT NULL,
                    grounding_report TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def write(
        self,
        request: str,
        video_ids: list[str],
        intent: str,
        retrieved_chunks: list[dict],
        grounding_report: dict | None = None,
        latency_ms: int = 0,
    ) -> str:
        trace_id = str(uuid.uuid4())
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO traces
                (trace_id, request, video_ids, intent, retrieved_chunks, grounding_report, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    request,
                    json.dumps(video_ids),
                    intent,
                    json.dumps(retrieved_chunks),
                    json.dumps(grounding_report or {}),
                    latency_ms,
                ),
            )
        return trace_id

    def recent(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT trace_id, request, video_ids, intent, grounding_report, latency_ms, created_at
                FROM traces ORDER BY created_at DESC, rowid DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "trace_id": row[0],
                "request": row[1],
                "video_ids": json.loads(row[2]),
                "intent": row[3],
                "grounding_report": json.loads(row[4]),
                "latency_ms": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]
