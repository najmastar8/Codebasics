from tube_trainer.ingest import (
    IngestionPipeline,
    IngestionRecord,
    TranscriptSegment,
    VideoMetadata,
    merge_caption_fragments,
)
from tube_trainer.main import get_welcome_message
from tube_trainer.rag import RagIndex, chunk_transcript
from tube_trainer.router import route_request
from tube_trainer.specialists import (
    explain,
    make_notes,
    make_plan,
    make_quiz,
    make_recipe,
    summarize,
)
from tube_trainer.memory import LearnerMemory
from tube_trainer.trace import TraceStore
from tube_trainer.export import export_markdown, export_anki_tsv


def test_get_welcome_message() -> None:
    assert get_welcome_message("Alice") == "Welcome to YouTube Recipe Writer, Alice!"


def test_resolve_video_id(tmp_path) -> None:
    pipeline = IngestionPipeline(tmp_path)

    assert pipeline.resolve_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert pipeline.resolve_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10") == "dQw4w9WgXcQ"


def test_merge_caption_fragments() -> None:
    segments = merge_caption_fragments(
        [
            TranscriptSegment("Hello", 0.0, 0.5),
            TranscriptSegment("world.", 0.5, 1.0),
            TranscriptSegment("Next", 1.0, 1.5),
        ]
    )

    assert segments[0].text == "Hello world."
    assert segments[0].start_s == 0.0
    assert segments[0].end_s == 1.0


def _record() -> IngestionRecord:
    return IngestionRecord(
        video_id="abcdefghijk",
        url="https://youtu.be/abcdefghijk",
        metadata=VideoMetadata(
            video_id="abcdefghijk",
            channel="Science Channel",
            chapters=(
                {"title": "Plants", "start_s": 0.0, "end_s": 20.0},
                {"title": "Sports", "start_s": 20.0, "end_s": 40.0},
            ),
        ),
        segments=(
            TranscriptSegment(
                "Photosynthesis uses sunlight and chlorophyll.",
                1.0,
                3.0,
            ),
            TranscriptSegment(
                "Plants convert light into chemical energy.",
                5.0,
                8.0,
            ),
            TranscriptSegment(
                "Basketball players dribble and shoot.",
                22.0,
                25.0,
            ),
        ),
        transcript_source="manual",
        quality="high",
    )


def test_chunk_transcript_uses_chapters_and_timestamps() -> None:
    chunks = chunk_transcript(_record(), target_words=6, overlap_words=0)

    assert [chunk.chapter_title for chunk in chunks] == ["Plants", "Sports"]
    assert chunks[0].start_s == 1.0
    assert chunks[0].end_s == 8.0
    assert chunks[0].video_id == "abcdefghijk"
    assert chunks[0].transcript_source == "manual"


def test_rag_index_returns_grounded_timestamp_citations(tmp_path) -> None:
    index = RagIndex(tmp_path)
    record = _record()
    index.index_record(record, target_words=6, overlap_words=0)

    retrieved = index.retrieve("chlorophyll sunlight", video_id=record.video_id)
    answer = index.answer("chlorophyll sunlight", video_id=record.video_id)

    assert retrieved
    assert retrieved[0].chapter_title == "Plants"
    assert "Transcript quality: high" in answer
    assert "[abcdefghijk@00:01](https://youtu.be/abcdefghijk?t=1)" in answer
    assert index.get_summary(record.video_id)
    assert index.get_summary(record.video_id, "Plants")


def test_rag_index_does_not_invent_missing_evidence(tmp_path) -> None:
    index = RagIndex(tmp_path)
    index.index_record(_record(), target_words=6, overlap_words=0)

    assert index.answer("quantum mechanics") == (
        "The transcript does not appear to cover that question."
    )


def test_router_routes_and_requires_clarification() -> None:
    assert route_request("Summarize this video in 10 bullets").intent == "summarize"
    assert route_request("Make quiz questions").intent == "quiz"
    assert route_request("Extract the recipe from this video").intent == "recipe"
    assert route_request("What is the recipe?").intent == "recipe"
    assert route_request("quiz and summarize").intent == "unclear"


def test_specialists_return_grounded_outputs(tmp_path) -> None:
    index = RagIndex(tmp_path)
    index.index_record(_record(), target_words=6, overlap_words=0)

    summary = summarize(index, ["abcdefghijk"])
    notes = make_notes(index, ["abcdefghijk"])
    quiz = make_quiz(index, ["abcdefghijk"], count=2)
    explanation = explain(index, ["abcdefghijk"], "chlorophyll")
    plan = make_plan(index, ["abcdefghijk"], weeks=2)

    assert "## Key points" in summary
    assert "## Study notes" in notes
    assert "Source:" in quiz
    assert "What does photosynthesis use?" in quiz
    assert "What do plants convert light into?" in quiz
    assert "What key term or concept" not in quiz
    assert "[abcdefghijk@00:01]" in summary
    assert all(
        line.startswith(("##", "**", "-"))
        for line in summary.splitlines()
    )
    assert "## Simple explanation" in explanation
    assert "### Week 2" in plan


def test_summary_and_quiz_use_transcript_facts_precisely(tmp_path) -> None:
    record = IngestionRecord(
        video_id="abcdefghijk",
        url="https://youtu.be/abcdefghijk",
        metadata=VideoMetadata(video_id="abcdefghijk"),
        segments=(
            TranscriptSegment(
                "Photosynthesis is the process plants use to make food.",
                2.0,
                5.0,
            ),
            TranscriptSegment(
                "Plants use chlorophyll to absorb sunlight.",
                6.0,
                9.0,
            ),
            TranscriptSegment(
                "Less sunlight causes slower plant growth.",
                10.0,
                13.0,
            ),
            TranscriptSegment(
                "Photosynthesis produces glucose.",
                14.0,
                16.0,
            ),
        ),
        transcript_source="manual",
        quality="high",
    )
    index = RagIndex(tmp_path)
    index.index_record(record, target_words=100, overlap_words=0)

    summary = summarize(index, [record.video_id], count=3)
    quiz = make_quiz(index, [record.video_id], count=5)

    assert "Photosynthesis is the process plants use to make food." in summary
    assert "[abcdefghijk@00:02]" in summary
    assert "What is photosynthesis?" in quiz
    assert "What do plants use?" in quiz
    assert "What does less sunlight cause?" in quiz
    assert "What does photosynthesis produce?" in quiz
    assert "Answer: **glucose**" in quiz
    assert "What key term or concept" not in quiz


def test_make_recipe_formats_transcript_details_with_timestamps(tmp_path) -> None:
    record = IngestionRecord(
        video_id="abcdefghijk",
        url="https://youtu.be/abcdefghijk",
        metadata=VideoMetadata(video_id="abcdefghijk"),
        segments=(
            TranscriptSegment(
                "For this recipe, we need 2 cups flour and one egg.",
                2.0,
                5.0,
            ),
            TranscriptSegment(
                "Mix the flour and egg together.",
                6.0,
                9.0,
            ),
            TranscriptSegment(
                "Bake at 350 degrees for 20 minutes.",
                10.0,
                13.0,
            ),
        ),
        transcript_source="manual",
        quality="high",
    )
    index = RagIndex(tmp_path)
    index.index_record(record, target_words=100, overlap_words=0)
    IngestionPipeline(tmp_path)._save_cache(record)

    recipe = make_recipe(index, [record.video_id])

    assert "## Recipe from video abcdefghijk" in recipe
    assert "### Ingredients" not in recipe
    assert "2 cups flour and one egg" not in recipe
    assert "### Instructions" not in recipe
    assert "Mix the flour and egg together." in recipe
    assert "### Timing and temperature" not in recipe
    assert "Bake at 350 degrees for 20 minutes." in recipe
    assert "[abcdefghijk@00:06]" in recipe
    assert "[abcdefghijk@00:10]" in recipe
    assert "[abcdefghijk@00:02]" not in recipe
    assert all(
        line.startswith(("##", "1.", "2."))
        for line in recipe.splitlines()
    )


def test_make_recipe_reports_when_transcript_has_no_recipe(tmp_path) -> None:
    index = RagIndex(tmp_path)
    index.index_record(_record(), target_words=100, overlap_words=0)

    assert "couldn't identify clear ingredients or cooking steps" in make_recipe(
        index,
        ["abcdefghijk"],
    )


def test_memory_preference_forget_and_sm2(tmp_path) -> None:
    memory = LearnerMemory(tmp_path)
    memory.set_preference("format", "concise bullets")
    assert memory.get_preference("format") == "concise bullets"

    memory.record_quiz_result("abcdefghijk", "chunking", False)
    assert memory.weak_topics() == ["chunking"]
    memory.record_quiz_result("abcdefghijk", "chunking", True)
    assert memory.weak_topics() == []

    memory.add_flashcard("card-1", "abcdefghijk", "chunking", "What is chunking?", "Text splitting")
    assert memory.due_flashcards()
    interval, _ = memory.review_flashcard("card-1", True)
    assert interval == 1

    memory.forget("format")
    assert memory.get_preference("format") is None


def test_trace_store_and_exports(tmp_path) -> None:
    traces = TraceStore(tmp_path)
    trace_id = traces.write(
        request="Summarize this video",
        video_ids=["abcdefghijk"],
        intent="summarize",
        retrieved_chunks=[{"chunk_id": "chunk-1"}],
        grounding_report={"supported_count": 1},
        latency_ms=12,
    )

    assert trace_id
    assert traces.recent()[0]["intent"] == "summarize"

    markdown = export_markdown("Study notes", "- Grounded note", tmp_path / "notes.md")
    anki = export_anki_tsv([("What is chunking?", "Text splitting")], tmp_path / "cards.tsv")
    assert markdown.read_text(encoding="utf-8").startswith("# Study notes")
    assert "What is chunking?" in anki.read_text(encoding="utf-8")
