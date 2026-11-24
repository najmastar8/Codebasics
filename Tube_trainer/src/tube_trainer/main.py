"""Entry point for YouTube Recipe Writer."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    import time

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tube_trainer.ingest import IngestionPipeline
    from tube_trainer.rag import RagIndex
else:
    from .ingest import IngestionPipeline
    from .rag import RagIndex

from tube_trainer.memory import LearnerMemory
from tube_trainer.router import route_request
from tube_trainer.specialists import (
    explain,
    make_notes,
    make_plan,
    make_quiz,
    make_recipe,
    summarize,
)
from tube_trainer.trace import TraceStore


def get_welcome_message(name: str = "Developer") -> str:
    """Return a simple startup message for the app."""
    return f"Welcome to YouTube Recipe Writer, {name}!"


def _ask_questions(rag_index: RagIndex, video_ids: list[str], cache_dir: str | Path) -> None:
    video_id = video_ids[0] if len(video_ids) == 1 else None
    selected_video_ids = video_ids if len(video_ids) > 1 else None
    memory = LearnerMemory(cache_dir)
    traces = TraceStore(cache_dir)
    while True:
        try:
            question = input("Ask YouTube Recipe Writer (blank to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question or question.lower() in {"q", "quit", "exit"}:
            return

        lowered = question.lower()
        if lowered.startswith("forget "):
            memory.forget(question[7:].strip())
            print("Removed matching preference or weak-topic memory.")
            continue
        if lowered.startswith("i prefer "):
            preference = question[9:].strip()
            memory.set_preference("format", preference)
            print(f"Saved preference: {preference}")
            continue

        route = route_request(question)
        if route.confidence < 0.6:
            print("Could you clarify what you want: recipe, summarize, notes, quiz, explanation, study plan, or a transcript question?")
            continue

        started = time.perf_counter()
        if route.intent == "summarize":
            output = summarize(rag_index, video_ids, int(route.params.get("count", 10)))
        elif route.intent == "recipe":
            output = make_recipe(rag_index, video_ids)
        elif route.intent == "notes":
            output = make_notes(rag_index, video_ids, question)
        elif route.intent == "quiz":
            output = make_quiz(rag_index, video_ids, int(route.params.get("count", 5)))
        elif route.intent == "explain":
            output = explain(rag_index, video_ids, question)
        elif route.intent == "plan":
            output = make_plan(rag_index, video_ids, int(route.params.get("weeks", 1)))
        else:
            output = rag_index.answer(
                question,
                video_id=video_id,
                video_ids=selected_video_ids,
            )
        print(output)
        traces.write(
            request=question,
            video_ids=video_ids,
            intent=route.intent,
            retrieved_chunks=[],
            latency_ms=round((time.perf_counter() - started) * 1000),
        )


def main() -> None:
    """Run the app's main entry point."""
    print(get_welcome_message())
    try:
        youtube_url = input("Enter a YouTube URL: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("No YouTube URL entered.")
        return

    if youtube_url:
        try:
            pipeline = IngestionPipeline()
            rag_index = RagIndex(pipeline.cache_dir)
            playlist_ids = pipeline.resolve_playlist_video_ids(youtube_url)
            indexed_video_ids: list[str] = []
            if playlist_ids:
                print(f"Found {len(playlist_ids)} videos in the playlist.")
                for video_id in playlist_ids:
                    record = pipeline.ingest(f"https://youtu.be/{video_id}")
                    chunks = rag_index.index_record(record)
                    indexed_video_ids.append(record.video_id)
                    print(
                        f"Ingested video {record.video_id}: {len(record.segments)} transcript segments "
                        f"({record.transcript_source}, {record.quality} quality)."
                    )
                    print(f"Indexed {len(chunks)} timestamped transcript chunks.")
            else:
                record = pipeline.ingest(youtube_url)
                chunks = rag_index.index_record(record)
                indexed_video_ids.append(record.video_id)
                print(
                    f"Ingested video {record.video_id}: {len(record.segments)} transcript segments "
                    f"({record.transcript_source}, {record.quality} quality)."
                )
                print(f"Indexed {len(chunks)} timestamped transcript chunks.")
                summary = rag_index.get_summary(record.video_id)
                if summary:
                    print(f"Video summary: {summary}")
            if indexed_video_ids:
                _ask_questions(rag_index, indexed_video_ids, pipeline.cache_dir)
        except (ValueError, RuntimeError) as exc:
            print(f"Ingestion failed: {exc}")


if __name__ == "__main__":
    main()
