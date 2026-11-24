# YouTube Recipe Writer

Turn YouTube cooking videos into structured recipes grounded in their transcripts.

## Project structure

- `src/tube_trainer/` – application source code
- `tests/` – automated tests
- `data/` – local datasets or generated files
- `config/` – configuration files

## How to run

### Prerequisites

- Python 3.10 or newer
- Internet access for loading YouTube transcripts
- Windows PowerShell commands are shown below; adapt activation and paths as needed on macOS or Linux

### Set up from a terminal

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

If PowerShell blocks `.venv\Scripts\Activate.ps1`, activate with Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

To create the environment and install dependencies without activating it, use:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

### Run the Streamlit interface

```powershell
python -m streamlit run src/tube_trainer/app.py
```

When running without activation, use:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src/tube_trainer/app.py
```

Streamlit prints a local URL, usually `http://localhost:8501`, and opens it in your browser.

### Run the command-line interface

```powershell
python -m tube_trainer.main
```

Enter a YouTube video or playlist URL when prompted. The app caches transcripts and indexes timestamped passages. Then enter a request such as:

- `Extract the recipe from this video`
- `Summarize this video in 10 bullets`
- `Make study notes`
- `Quiz me on this video`

Enter a blank line or `q` to exit the prompt.

### Run tests and the regression gate

```powershell
python -m pytest
python evals/run_gate.py
```

The gate writes metrics to `evals/reports/latest.json`.

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
