# TubeTutor

TubeTutor is a personal study assistant that turns YouTube videos and playlists into grounded learning materials: summaries, study notes, flashcards, quizzes, and revision plans.

This repository is a starter scaffold aligned to the project spec:
- LangGraph orchestration
- Transcript ingestion and caching
- RAG with hybrid retrieval and citations
- Router with multiple strategies
- Memory and spaced repetition
- Grounding checks and eval harness
- Streamlit UI and export tools

## Repository layout

- `src/tubetutor/` – application package
- `src/tubetutor/ingest/` – transcript fetching, cleaning, metadata
- `src/tubetutor/rag/` – chunking, indexing, retrieval, reranking
- `src/tubetutor/router/` – request routing strategies
- `src/tubetutor/memory/` – memory, weak topic tracking, scheduler
- `src/tubetutor/agents/` – summarizer, notes, quiz, QA, planner, explainer
- `src/tubetutor/guardrails/` – grounding validation
- `src/tubetutor/llm/` – LLM client and prompts
- `src/tubetutor/export/` – markdown and Anki export
- `src/tubetutor/app/` – Streamlit app
- `data/` – transcript cache and eval artifacts
- `evals/` – evaluation scripts and reports
- `tests/` – smoke and unit tests

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run a smoke check:
   ```bash
   python -m pytest -q
   ```
4. Start the app:
   ```bash
   streamlit run src/tubetutor/app/streamlit_app.py
   ```

## Ingestion smoke usage

Ingest a video or playlist member into the local SQLite cache:

```python
from tubetutor.ingest import IngestionPipeline

record = IngestionPipeline().ingest("https://youtu.be/VIDEO_ID")
print(record.title)
print(record.transcript_source)
for sentence in record.sentences[:5]:
    print(sentence.start_s, sentence.text)
```

A rerun for the same video is served from `data/cache/transcripts.sqlite3`. Pass `force_refresh=True` to bypass the cache.

For an interactive test that prompts you for a URL, run:

```bash
python try_ingestion.py
```

## Milestones

This scaffold is organized around the spec's milestones:
1. Ingestion and transcript cache
2. Core RAG and cited Q&A
3. Summaries and notes with grounding
4. Routing strategies and clarify path
5. Quizzes and flashcards
6. Memory and weak-topic weighting
7. Planner and explainer
8. Regression gate and polish

## Notes

The project intentionally keeps the initial code minimal and runnable, while making the architecture and module boundaries align with the spec so the next implementation steps are straightforward.
