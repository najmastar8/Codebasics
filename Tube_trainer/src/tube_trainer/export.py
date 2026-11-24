"""Exports for study notes and flashcards."""

from __future__ import annotations

import csv
from pathlib import Path


def export_markdown(title: str, content: str, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return path


def export_anki_tsv(cards: list[tuple[str, str]], output_path: str | Path) -> Path:
    """Write an Anki-compatible two-column tab-separated import file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["Front", "Back"])
        writer.writerows(cards)
    return path
