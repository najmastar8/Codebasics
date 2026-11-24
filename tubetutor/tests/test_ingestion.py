from pathlib import Path

import ingestion_pipeline

from tubetutor.ingest.cache import TranscriptCache
from tubetutor.ingest.clean import CaptionFragment, clean_caption_fragments
from tubetutor.ingest.resolve import resolve_video_id


def test_resolve_video_id_from_watch_url() -> None:
    assert resolve_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_resolve_video_id_from_short_url() -> None:
    assert resolve_video_id("https://youtu.be/dQw4w9WgXcQ?t=30") == "dQw4w9WgXcQ"


def test_clean_caption_fragments_preserves_timestamps() -> None:
    fragments = [
        CaptionFragment("Hello world.", 12.0, 2.0),
        CaptionFragment("This is a test.", 14.0, 2.0),
    ]
    sentences, removed_sponsor = clean_caption_fragments(fragments)
    assert [sentence.text for sentence in sentences] == ["Hello world.", "This is a test."]
    assert sentences[0].start_s == 12
    assert sentences[1].end_s == 16
    assert removed_sponsor is False


def test_transcript_cache_round_trip(tmp_path: Path) -> None:
    cache = TranscriptCache(tmp_path / "cache.sqlite3")
    from tubetutor.ingest.models import TranscriptRecord, TranscriptSentence

    record = TranscriptRecord(
        video_id="testvideo01",
        sentences=[TranscriptSentence("Cached sentence.", 5, 8)],
        title="Test video",
        transcript_source="manual",
    )

    cache.put(record)
    loaded = cache.get("testvideo01")
    assert loaded is not None
    assert loaded.title == "Test video"
    assert loaded.sentences[0].start_s == 5


def test_ingestion_cli_passes_url_and_refresh_option(monkeypatch, capsys) -> None:
    calls = {}

    class FakePipeline:
        def ingest(self, url: str, force_refresh: bool = False):
            calls["url"] = url
            calls["force_refresh"] = force_refresh
            from tubetutor.ingest.models import TranscriptRecord, TranscriptSentence

            return TranscriptRecord(
                video_id="dQw4w9WgXcQ",
                sentences=[TranscriptSentence("Example transcript.", 0, 3)],
                title="Example",
                transcript_source="manual",
                transcript_quality="good",
            )

    monkeypatch.setattr(ingestion_pipeline, "IngestionPipeline", FakePipeline)
    ingestion_pipeline.main(
        ["https://youtu.be/dQw4w9WgXcQ", "--force-refresh"]
    )

    assert calls == {
        "url": "https://youtu.be/dQw4w9WgXcQ",
        "force_refresh": True,
    }
    assert "Example transcript." in capsys.readouterr().out
