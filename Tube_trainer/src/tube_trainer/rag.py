"""Transcript chunking, local retrieval, and timestamp-grounded answers."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .ingest import IngestionRecord, TranscriptSegment


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_id: str
    text: str
    video_id: str
    start_s: float
    end_s: float
    chapter_title: str
    channel: str
    transcript_source: str
    quality: str


@dataclass(frozen=True)
class RetrievedChunk(TranscriptChunk):
    score: float


WORD_PATTERN = re.compile(r"[A-Za-z0-9_']+")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in WORD_PATTERN.findall(text) if token.lower() not in STOP_WORDS]


def _make_chunk(
    segments: Sequence[TranscriptSegment],
    video_id: str,
    channel: str,
    transcript_source: str,
    quality: str,
    chapter_title: str,
) -> TranscriptChunk:
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    start_s = segments[0].start_s
    end_s = segments[-1].end_s
    identity = "\0".join((video_id, str(start_s), str(end_s), chapter_title, text))
    chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return TranscriptChunk(
        chunk_id=chunk_id,
        text=text,
        video_id=video_id,
        start_s=start_s,
        end_s=end_s,
        chapter_title=chapter_title,
        channel=channel,
        transcript_source=transcript_source,
        quality=quality,
    )


def _fixed_chunks(
    segments: Sequence[TranscriptSegment],
    video_id: str,
    channel: str,
    transcript_source: str,
    quality: str,
    target_words: int,
    overlap_words: int,
    chapter_title: str = "",
) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    start = 0

    while start < len(segments):
        end = start
        word_count = 0
        while end < len(segments):
            word_count += len(WORD_PATTERN.findall(segments[end].text))
            end += 1
            if word_count >= target_words:
                break

        included = segments[start:end]
        if included:
            chunks.append(
                _make_chunk(
                    included,
                    video_id,
                    channel,
                    transcript_source,
                    quality,
                    chapter_title,
                )
            )
        if end >= len(segments):
            break

        next_start = end
        overlap_count = 0
        while next_start > start + 1 and overlap_count < overlap_words:
            next_start -= 1
            overlap_count += len(WORD_PATTERN.findall(segments[next_start].text))
        start = next_start

    return chunks


def chunk_transcript(
    record: IngestionRecord,
    target_words: int = 400,
    overlap_words: int = 60,
) -> list[TranscriptChunk]:
    """Split transcript on sentence boundaries, preserving source timestamps."""
    if target_words <= 0:
        raise ValueError("target_words must be greater than zero")
    if overlap_words < 0 or overlap_words >= target_words:
        raise ValueError("overlap_words must be between zero and target_words")

    segments = [segment for segment in record.segments if segment.text.strip()]
    if not segments:
        return []

    channel = record.metadata.channel
    chapters = sorted(
        record.metadata.chapters,
        key=lambda chapter: float(chapter.get("start_s", 0)),
    )
    chunks: list[TranscriptChunk] = []
    if chapters:
        groups: list[tuple[str, list[TranscriptSegment]]] = []
        for segment in segments:
            title = ""
            for chapter in chapters:
                chapter_start = float(chapter.get("start_s", 0))
                chapter_end = float(chapter.get("end_s", 0))
                if segment.start_s < chapter_end and segment.end_s > chapter_start:
                    title = str(chapter.get("title", ""))
                    break
            if not groups or groups[-1][0] != title:
                groups.append((title, []))
            groups[-1][1].append(segment)

        for title, chapter_segments in groups:
            chunks.extend(
                _fixed_chunks(
                    chapter_segments,
                    record.video_id,
                    channel,
                    record.transcript_source,
                    record.quality,
                    target_words,
                    overlap_words,
                    title,
                )
            )
    else:
        chunks = _fixed_chunks(
            segments,
            record.video_id,
            channel,
            record.transcript_source,
            record.quality,
            target_words,
            overlap_words,
        )
    return chunks


def _extractive_summary(chunks: Sequence[TranscriptChunk], max_sentences: int = 3) -> str:
    sentences: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for sentence in SENTENCE_PATTERN.split(chunk.text):
            sentence = sentence.strip()
            normalized = sentence.casefold()
            if sentence and normalized not in seen:
                sentences.append(sentence)
                seen.add(normalized)
    if not sentences:
        return ""

    frequencies = Counter(token for sentence in sentences for token in _tokens(sentence))
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (
            -sum(frequencies[token] for token in _tokens(item[1]))
            / max(len(_tokens(item[1])), 1),
            item[0],
        ),
    )
    chosen = sorted(index for index, _ in ranked[:max_sentences])
    return " ".join(sentences[index] for index in chosen)


def _format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, remaining_seconds = divmod(total, 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes:02d}:{remaining_seconds:02d}"


class RagIndex:
    """Persist transcript chunks and retrieve citation-ready evidence with BM25 and TF-IDF."""

    def __init__(self, cache_dir: str | Path = "data") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.cache_dir / "tube_trainer.sqlite3"
        self._initialize_database()

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    start_s REAL NOT NULL,
                    end_s REAL NOT NULL,
                    chapter_title TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    transcript_source TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    vector_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS rag_chunks_video_idx
                ON rag_chunks(video_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS rag_chunks_channel_idx
                ON rag_chunks(channel)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_summaries (
                    video_id TEXT NOT NULL,
                    chapter_title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    PRIMARY KEY(video_id, chapter_title)
                )
                """
            )

    def index_record(
        self,
        record: IngestionRecord,
        target_words: int = 400,
        overlap_words: int = 60,
    ) -> list[TranscriptChunk]:
        """Create and persist chunks and deterministic extractive summaries."""
        chunks = chunk_transcript(record, target_words, overlap_words)
        chapter_chunks: dict[str, list[TranscriptChunk]] = {}
        for chunk in chunks:
            chapter_chunks.setdefault(chunk.chapter_title, []).append(chunk)
        summaries = [
            (record.video_id, chapter, _extractive_summary(chapter_group))
            for chapter, chapter_group in chapter_chunks.items()
            if chapter
        ]
        if chunks:
            summaries.append((record.video_id, "", _extractive_summary(chunks)))

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("BEGIN")
            connection.execute("DELETE FROM rag_chunks WHERE video_id = ?", (record.video_id,))
            connection.execute("DELETE FROM rag_summaries WHERE video_id = ?", (record.video_id,))
            connection.executemany(
                """
                INSERT INTO rag_chunks (
                    chunk_id, video_id, text, start_s, end_s, chapter_title,
                    channel, transcript_source, quality, vector_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.video_id,
                        chunk.text,
                        chunk.start_s,
                        chunk.end_s,
                        chunk.chapter_title,
                        chunk.channel,
                        chunk.transcript_source,
                        chunk.quality,
                        "{}",
                    )
                    for chunk in chunks
                ],
            )
            indexed_rows = connection.execute(
                "SELECT chunk_id, text FROM rag_chunks"
            ).fetchall()
            all_tokens = [_tokens(row[1]) for row in indexed_rows]
            document_count = len(all_tokens)
            all_frequencies = Counter(
                token for tokens in all_tokens for token in set(tokens)
            )
            connection.executemany(
                "UPDATE rag_chunks SET vector_json = ? WHERE chunk_id = ?",
                [
                    (
                        json.dumps(
                            self._vectorize(tokens, all_frequencies, document_count),
                            sort_keys=True,
                        ),
                        row[0],
                    )
                    for row, tokens in zip(indexed_rows, all_tokens)
                ],
            )
            connection.executemany(
                """
                INSERT INTO rag_summaries(video_id, chapter_title, summary)
                VALUES (?, ?, ?)
                """,
                summaries,
            )
        return chunks

    @staticmethod
    def _vectorize(
        tokens: Iterable[str],
        document_frequencies: Counter[str],
        document_count: int,
    ) -> dict[str, float]:
        counts = Counter(tokens)
        vector: dict[str, float] = {}
        for token, count in counts.items():
            inverse_frequency = math.log(
                (document_count + 1) / (document_frequencies[token] + 1)
            ) + 1
            vector[token] = (1 + math.log(count)) * inverse_frequency
        return vector

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot_product = sum(value * right.get(token, 0.0) for token, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        video_id: str | None = None,
        channel: str | None = None,
        video_ids: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Combine BM25 and sparse TF-IDF cosine ranks using reciprocal-rank fusion."""
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        filters: list[str] = []
        parameters: list[str] = []
        if video_id is not None:
            filters.append("video_id = ?")
            parameters.append(video_id)
        elif video_ids is not None:
            if not video_ids:
                return []
            placeholders = ", ".join("?" for _ in video_ids)
            filters.append(f"video_id IN ({placeholders})")
            parameters.extend(video_ids)
        if channel is not None:
            filters.append("channel = ?")
            parameters.append(channel)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT chunk_id, video_id, text, start_s, end_s, chapter_title,
                       channel, transcript_source, quality, vector_json
                FROM rag_chunks
                {where_clause}
                """,
                parameters,
            ).fetchall()
        if not rows:
            return []

        document_tokens = [_tokens(row[2]) for row in rows]
        document_frequencies = Counter(
            token for tokens in document_tokens for token in set(tokens)
        )
        document_count = len(rows)
        average_length = sum(map(len, document_tokens)) / document_count or 1.0
        query_vector = self._vectorize(query_tokens, document_frequencies, document_count)
        query_counts = Counter(query_tokens)

        bm25_scores: list[float] = []
        vector_scores: list[float] = []
        for row, tokens in zip(rows, document_tokens):
            term_counts = Counter(tokens)
            length_norm = 1.5 * (1 - 0.75 + 0.75 * len(tokens) / average_length)
            bm25 = 0.0
            for token, query_count in query_counts.items():
                frequency = term_counts[token]
                if not frequency:
                    continue
                idf = math.log(
                    1 + (document_count - document_frequencies[token] + 0.5)
                    / (document_frequencies[token] + 0.5)
                )
                bm25 += (
                    query_count
                    * idf
                    * frequency
                    * 2.5
                    / (frequency + length_norm)
                )
            bm25_scores.append(bm25)
            document_vector = json.loads(row[9])
            vector_scores.append(self._cosine(query_vector, document_vector))

        bm25_ranks = sorted(
            range(document_count), key=lambda index: (-bm25_scores[index], index)
        )
        vector_ranks = sorted(
            range(document_count), key=lambda index: (-vector_scores[index], index)
        )
        fused_scores: dict[int, float] = {}
        for scores, ranks in (
            (bm25_scores, bm25_ranks),
            (vector_scores, vector_ranks),
        ):
            for rank, index in enumerate(ranks, start=1):
                if scores[index] > 0:
                    fused_scores[index] = fused_scores.get(index, 0.0) + 1 / (60 + rank)

        ordered = sorted(fused_scores, key=lambda index: (-fused_scores[index], index))
        return [
            RetrievedChunk(
                chunk_id=rows[index][0],
                video_id=rows[index][1],
                text=rows[index][2],
                start_s=rows[index][3],
                end_s=rows[index][4],
                chapter_title=rows[index][5],
                channel=rows[index][6],
                transcript_source=rows[index][7],
                quality=rows[index][8],
                score=fused_scores[index],
            )
            for index in ordered[:top_k]
        ]

    def get_summary(self, video_id: str, chapter_title: str | None = None) -> str | None:
        """Return the stored full-video summary or a summary for a named chapter."""
        chapter = chapter_title or ""
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT summary FROM rag_summaries
                WHERE video_id = ? AND chapter_title = ?
                """,
                (video_id, chapter),
            ).fetchone()
        return row[0] if row else None

    def get_chunks(self, video_id: str) -> list[TranscriptChunk]:
        """Return indexed transcript chunks in timestamp order."""
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, text, video_id, start_s, end_s, chapter_title,
                       channel, transcript_source, quality
                FROM rag_chunks
                WHERE video_id = ?
                ORDER BY start_s, end_s, chunk_id
                """,
                (video_id,),
            ).fetchall()
        return [TranscriptChunk(*row) for row in rows]

    def get_transcript_segments(self, video_id: str) -> list[TranscriptSegment]:
        """Return cached transcript segments with their individual timestamps."""
        with sqlite3.connect(self.database_path) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ingestions'"
            ).fetchone()
            if not table:
                return []
            row = connection.execute(
                "SELECT segments_json FROM ingestions WHERE video_id = ?",
                (video_id,),
            ).fetchone()
        if not row:
            return []
        return [
            TranscriptSegment(**segment)
            for segment in json.loads(row[0])
        ]

    def answer(
        self,
        question: str,
        top_k: int = 5,
        video_id: str | None = None,
        channel: str | None = None,
        video_ids: Sequence[str] | None = None,
    ) -> str:
        """Return transcript evidence with timestamp links, without inventing answers."""
        results = self.retrieve(question, top_k, video_id, channel, video_ids)
        if not results:
            return "The transcript does not appear to cover that question."

        quality = ", ".join(sorted({chunk.quality for chunk in results}))
        lines = [f"Transcript quality: {quality}. Relevant transcript passages:"]
        for chunk in results:
            timestamp = int(chunk.start_s)
            label = _format_timestamp(chunk.start_s)
            citation = (
                f"[{chunk.video_id}@{label}]"
                f"(https://youtu.be/{chunk.video_id}?t={timestamp})"
            )
            lines.append(f"- {chunk.text} {citation}")
        return "\n".join(lines)
