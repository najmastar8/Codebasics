# YouTube Recipe Writer

Turn YouTube cooking videos into structured recipes grounded in their transcripts.

## Project structure

- `src/tube_trainer/` – application source code
- `tests/` – automated tests
- `data/` – local datasets or generated files
- `config/` – configuration files

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python -m tube_trainer.main
   ```
4. Enter a YouTube cooking video URL. The app caches its transcript and indexes timestamped passages.
5. Select **Extract recipe from indexed video** or enter `Extract the recipe from this video` to get a simple numbered recipe with links to its source timestamps. Other study tools and transcript questions are also available.
6. In the CLI, enter a recipe request at the prompt. Enter a blank line or `q` to exit.

The recipe extractor is deterministic and transcript-grounded; it does not use an LLM or fill in amounts and steps that the video does not state. Local SQLite stores transcripts, indexes, learner memory, and request traces.

## Streamlit UI

After installing dependencies in the same Python environment, launch the browser interface:

```bash
python -m streamlit run src/tube_trainer/app.py
```

Using `python -m streamlit` avoids Windows `PATH` issues where the `streamlit` command is installed but its Scripts directory is not available in the terminal.

Paste a YouTube cooking video URL and select **Ingest**. Then choose **Extract recipe from indexed video**, or ask for the recipe in the learning prompt. The output is a simple numbered list of cooking steps with timestamp links back to the video. Ingredient amounts and cooking times are included inline only when the spoken step mentions them.

Ingredient and cooking-action recognition is based on spoken wording, so recipe details omitted from narration may not be detected.

## Exports and regression gate

Use `src/tube_trainer/export.py` to export Markdown and Anki-compatible TSV files. Run the versioned routing and test regression gate with:

```bash
python evals/run_gate.py
```

The gate writes metrics to `evals/reports/latest.json`. Request traces are stored in the local SQLite database with a trace ID and latency.

The local retrieval index combines BM25 keyword search with sparse TF-IDF vectors. It does not call an LLM or generate semantic answers: it returns relevant transcript evidence and says when it cannot find evidence. Transcript chunks, summaries, and indexes are stored in `data/tube_trainer.sqlite3`.
