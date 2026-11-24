"""Lightweight grounding validation for generated passages."""

from __future__ import annotations

from dataclasses import dataclass

from .rag import RetrievedChunk


@dataclass(frozen=True)
class GroundingReport:
    supported_count: int
    unsupported_count: int
    citation_mismatch_count: int


def validate_claims(claims: list[str], evidence: list[RetrievedChunk]) -> GroundingReport:
    supported = 0
    unsupported = 0
    mismatches = 0
    evidence_text = " ".join(chunk.text.lower() for chunk in evidence)
    for claim in claims:
        words = [word.lower().strip(".,;:!?()[]") for word in claim.split() if len(word) > 4]
        if not words:
            unsupported += 1
            continue
        overlap = sum(word in evidence_text for word in words) / len(words)
        if overlap >= 0.45:
            supported += 1
        else:
            unsupported += 1
            mismatches += 1
    return GroundingReport(supported, unsupported, mismatches)
