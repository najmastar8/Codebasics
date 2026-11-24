from __future__ import annotations

from typing import Any

from .state import TubeTutorState


def build_graph() -> dict[str, Any]:
    """Return a skeleton graph definition for the TubeTutor workflow.

    This is intentionally lightweight and meant to establish the architecture,
    not full production orchestration yet.
    """
    return {
        "nodes": [
            "ingest",
            "load_memory",
            "route_request",
            "specialist_agents",
            "retrieval_service",
            "grounding_check",
            "write_memory",
            "final_output",
        ],
        "edges": [
            ("ingest", "load_memory"),
            ("load_memory", "route_request"),
            ("route_request", "specialist_agents"),
            ("specialist_agents", "retrieval_service"),
            ("retrieval_service", "grounding_check"),
            ("grounding_check", "write_memory"),
            ("write_memory", "final_output"),
        ],
    }


def smoke_state() -> TubeTutorState:
    return TubeTutorState(
        request="Summarize this video in 10 bullets.",
        video_ids=["abc123"],
        intent="summarize",
        confidence=0.92,
        route_reason="Direct summary request for a known video.",
        scope="single_video",
        params={"length": "10 bullets"},
        trace_id="demo-trace-001",
    )
