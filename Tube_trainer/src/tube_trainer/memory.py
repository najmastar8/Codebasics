"""Local learner memory and spaced-repetition scheduling."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path


class LearnerMemory:
    def __init__(self, cache_dir: str | Path = "data") -> None:
        self.database_path = Path(cache_dir) / "tube_trainer.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS learner_preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            connection.execute("CREATE TABLE IF NOT EXISTS episodic_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, video_id TEXT, topic TEXT, correct INTEGER, details TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            connection.execute("CREATE TABLE IF NOT EXISTS weak_topics (topic TEXT PRIMARY KEY, misses INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            connection.execute("CREATE TABLE IF NOT EXISTS flashcards (card_id TEXT PRIMARY KEY, video_id TEXT NOT NULL, topic TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL, ease REAL NOT NULL DEFAULT 2.5, interval_days INTEGER NOT NULL DEFAULT 0, due_date TEXT NOT NULL)")

    def set_preference(self, key: str, value: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("INSERT INTO learner_preferences(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (key, value))

    def get_preference(self, key: str) -> str | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT value FROM learner_preferences WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def forget(self, key: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DELETE FROM learner_preferences WHERE key=?", (key,))
            connection.execute("DELETE FROM weak_topics WHERE topic=?", (key,))

    def record_quiz_result(self, video_id: str, topic: str, correct: bool) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("INSERT INTO episodic_events(event_type,video_id,topic,correct,details) VALUES ('quiz_attempt',?,?,?,?)", (video_id, topic, 1 if correct else 0, ""))
            if correct:
                connection.execute("DELETE FROM weak_topics WHERE topic=?", (topic,))
            else:
                connection.execute("INSERT INTO weak_topics(topic,misses) VALUES (?,1) ON CONFLICT(topic) DO UPDATE SET misses=misses+1, updated_at=CURRENT_TIMESTAMP", (topic,))

    def weak_topics(self) -> list[str]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute("SELECT topic FROM weak_topics ORDER BY misses DESC, updated_at DESC LIMIT 10").fetchall()
        return [row[0] for row in rows]

    def add_flashcard(self, card_id: str, video_id: str, topic: str, question: str, answer: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("INSERT OR REPLACE INTO flashcards(card_id,video_id,topic,question,answer,due_date) VALUES (?,?,?,?,?,?)", (card_id, video_id, topic, question, answer, date.today().isoformat()))

    def review_flashcard(self, card_id: str, correct: bool) -> tuple[int, str]:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT ease, interval_days FROM flashcards WHERE card_id=?", (card_id,)).fetchone()
            if not row:
                raise KeyError("Unknown flashcard")
            ease, interval = float(row[0]), int(row[1])
            if correct:
                ease = max(1.3, ease + 0.1)
                interval = 1 if interval == 0 else min(365, round(interval * ease))
            else:
                ease = max(1.3, ease - 0.2)
                interval = 0
            due = date.today() if interval == 0 else date.today() + timedelta(days=interval)
            connection.execute("UPDATE flashcards SET ease=?,interval_days=?,due_date=? WHERE card_id=?", (ease, interval, due.isoformat(), card_id))
        return interval, due.isoformat()

    def due_flashcards(self) -> list[tuple[str, str, str]]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute("SELECT card_id,question,answer FROM flashcards WHERE due_date<=? ORDER BY due_date", (date.today().isoformat(),)).fetchall()
        return [(row[0], row[1], row[2]) for row in rows]
