from __future__ import annotations

import re
from dataclasses import dataclass


_FILLER_RE = re.compile(
    r"\b(um|uh|you know|like|sort of|kind of)\b",
    re.IGNORECASE,
)
_SPONSOR_RE = re.compile(
    r"(?:this (?:video|episode) is sponsored by|sponsor(?:ed)? segment|use code .+? at checkout)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CaptionFragment:
    text: str
    start: float
    duration: float = 0.0


@dataclass(frozen=True)
class Sentence:
    text: str
    start_s: int
    end_s: int


def remove_filler(text: str) -> str:
    text = _FILLER_RE.sub("", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def clean_caption_fragments(fragments: list[CaptionFragment]) -> tuple[list[Sentence], bool]:
    """Merge fragments into sentence-like units while preserving timestamp bounds."""
    sentences: list[Sentence] = []
    removed_sponsor_segment = False
    buffer: list[str] = []
    start = 0.0

    for fragment in fragments:
        text = (fragment.text or "").strip()
        if not text:
            continue
        if _SPONSOR_RE.search(text):
            removed_sponsor_segment = True
            continue

        text = remove_filler(text)
        if not text:
            continue
        if not buffer:
            start = fragment.start

        buffer.append(text)
        merged = " ".join(buffer)
        if re.search(r"[.!?](?:\s*['\"\)])?$", merged) or len(merged) >= 260:
            end = fragment.start + max(fragment.duration, 0.0)
            sentences.append(Sentence(merged, int(round(start)), int(round(end))))
            buffer = []

    if buffer:
        start_s = int(round(start))
        end_s = int(round(max((fragment.start + fragment.duration for fragment in fragments), default=start)))
        sentences.append(Sentence(" ".join(buffer), start_s, end_s))

    return sentences, removed_sponsor_segment
