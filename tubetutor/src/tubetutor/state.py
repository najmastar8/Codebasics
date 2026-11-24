from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkRecord:
    """A single retrieved transcript chunk with citation metadata."""

    chunk_id: str
    text: str
    video_id: str
    start_s: int
    end_s: int
    score: float = 0.0
    chapter_title: str | None = None
    channel: str | None = None
    transcript_source: str | None = None


@dataclass
class TubeTutorState:
    """Shared graph state for the TubeTutor workflow."""

    request: str = ""
    video_ids: list[str] = field(default_factory=list)
    intent: str = "unclear"
    confidence: float = 0.0
    route_reason: str = ""
    scope: str = "single_video"
    params: dict[str, Any] = field(default_factory=dict)
    retrieved_chunks: list[ChunkRecord] = field(default_factory=list)
    memory_context: dict[str, Any] = field(default_factory=dict)
    draft: str = ""
    citations: list[str] = field(default_factory=list)
    grounding_report: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
