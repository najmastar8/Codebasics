"""Deterministic request routing for the YouTube Recipe Writer CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    intent: str
    confidence: float
    reason: str
    params: dict[str, object]


_PATTERNS = (
    ("recipe", re.compile(r"\b(recipe|ingredients?|cooking instructions)\b", re.I)),
    ("summarize", re.compile(r"\b(summar(?:ize|y|izing)|tldr|key takeaway|overview)\b", re.I)),
    ("notes", re.compile(r"\b(notes|study (material|guide)|concept|definition)\b", re.I)),
    ("quiz", re.compile(r"\b(quiz|test|mcq|multiple.?choice|flashcard|practice)\b", re.I)),
    ("explain", re.compile(r"\b(explain|simpl(e|ify)|analogy|understand)\b", re.I)),
    ("plan", re.compile(r"\b(plan|schedule|week|study for|prepare)\b", re.I)),
    ("qa", re.compile(r"\b(at what|where|what|why|how|which|when|question)\b", re.I)),
)


def route_request(request: str) -> Route:
    text = request.strip()
    if not text:
        return Route("unclear", 0.0, "Blank request", {})

    matches = [(intent, pattern.search(text) is not None) for intent, pattern in _PATTERNS]
    matched = [intent for intent, found in matches if found]
    if "recipe" in matched and "qa" in matched:
        matched.remove("qa")
    if len(matched) == 1:
        params: dict[str, object] = {}
        length = re.search(r"(\d+)\s*(bullets?|minutes?|questions?|weeks?)", text, re.I)
        if length:
            params["count"] = int(length.group(1))
        if matched[0] == "plan":
            weeks = re.search(r"(\d+)\s*weeks?", text, re.I)
            params["weeks"] = int(weeks.group(1)) if weeks else 1
        return Route(matched[0], 0.85, "Matched a specialist intent", params)

    if not matched:
        return Route("qa", 0.55, "Treating the request as a transcript question", {})
    return Route("unclear", 0.45, "Request matches more than one specialist", {"matched_intents": matched})
