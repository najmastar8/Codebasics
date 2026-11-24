# TubeTutor: YouTube-to-Learning-Materials Agent

**Status:** Working specification v0.1  
**Working name:** TubeTutor  
**Project type:** Personal practice project for RAG, memory, routing, agentic orchestration, and quality evaluation

## 1. Purpose

TubeTutor converts YouTube videos and playlists into grounded learning materials:

- Summaries
- Study notes
- Flashcards
- Quizzes
- Study plans
- Timestamp-linked answers
- Simplified explanations

The system should remember the learner's goals, level, preferences, studied material, quiz performance, weak topics, and review schedule, then adapt future outputs accordingly.

### Success criteria

| Area | Target |
|---|---|
| Routing | At least 90% routing accuracy; ambiguous requests receive a clarifying question |
| RAG | Every note, answer, quiz item, and factual claim is grounded in transcript text and cites a video and timestamp |
| Memory | The system retains goals, verified quiz results, preferences, weak topics, and revision schedules |
| Quality | Faithfulness, coverage, citation accuracy, quiz quality, retrieval quality, and memory correctness are measured through a hand-labelled evaluation set |

### Non-goals

- Downloading or redistributing video content
- A public multi-user service
- A mobile application
- Commercial or high-scale distribution
- Storing full transcripts in a public repository

The system is for personal study use, with local caching of transcripts.

## 2. Key scenarios

| Request | Specialist | Expected behavior |
|---|---|---|
| "Summarize this video in 10 bullets." | Summarizer | Create a concise summary grounded in the video with timestamps |
| "Make study notes from this playlist." | Notes writer | Produce structured notes across several videos |
| "Quiz me on the RAG evaluation lecture." | Quiz maker | Weight questions toward weak topics from prior quizzes |
| "At what point does he explain chunking?" | Q&A | Answer with a timestamp link |
| "I did not understand reranking, explain it simply." | Explainer | Re-explain the cited passage with an analogy and optional check question |
| "Plan three weeks of study from these 12 videos." | Planner | Build a schedule respecting the learner's time and goals |
| "Help me learn." | Clarifier | Ask what the learner wants to achieve |

## 3. System architecture

TubeTutor uses a LangGraph state graph with ingestion, memory loading, routing, specialist generation, retrieval, grounding validation, memory updates, and traceable output.

```text
User request and optional video URL or playlist
                    |
                    v
       [Ingest if needed]
   Transcript -> metadata -> cleanup
   -> chunk -> summary nodes -> index
                    |
                    v
       [Load short-term and long-term memory]
                    |
                    v
          [Router + scope]
                    |
       low confidence --> Clarify --> User
                    |
                    v
  Summarizer | Notes | Quiz | Q&A | Explainer | Planner
                    |
             Retrieval + memory
                    |
                    v
            [Grounding check]
                    |
                    v
            [Write memory]
                    |
                    v
          Output + timestamps + trace
```

### Shared state

The graph state must contain:

- `request`
- `video_ids`
- `intent`
- `confidence`
- `route_reason`
- `scope`
- `params`
- `retrieved_chunks`
- `memory_context`
- `draft`
- `citations`
- `grounding_report`
- `trace_id`

Each retrieved chunk must include:

- Chunk ID
- Text
- Video ID
- Start timestamp
- End timestamp
- Relevance score
- Chapter title, when available
- Channel
- Transcript source

## 4. Functional requirements

### 4.1 Ingestion

1. Resolve a YouTube URL to a video ID.
2. Expand playlists into video IDs.
3. Fetch manual transcripts before automatic transcripts.
4. Attempt the following transcript sources:
   - `youtube-transcript-api`
   - Audio download using `yt-dlp`, followed by local or API Whisper transcription
5. Collect metadata:
   - Title
   - Channel
   - Duration
   - Upload date
   - Description
   - Chapter markers
6. Merge caption fragments into sentences while preserving per-sentence timestamps.
7. Remove detectable filler and sponsor segments.
8. Mark each transcript as `manual`, `auto`, or `whisper`.
9. Store a transcript-quality flag and surface it to the user in generated answers.
10. Cache transcripts, metadata, chunks, summaries, and indexes by video ID in SQLite and local files.
11. Make cached runs deterministic and suitable for reproducible evaluations.

### 4.2 Chunking

Implement two chunking strategies behind a shared interface:

- **Chapter-aware chunking:** use creator chapters when available; otherwise detect topic shifts using embedding similarity between sliding windows.
- **Fixed-window chunking:** use approximately 300–500 tokens with overlap, aligned to sentence boundaries.

Each chunk must carry:

- `video_id`
- `start_s`
- `end_s`
- `chapter_title`
- `channel`
- `transcript_source`

Create hierarchical summary nodes:

1. A short summary for each chapter.
2. A short summary for the complete video.

These summaries support whole-video questions without retrieving every chunk.

### 4.3 Retrieval

The retrieval index combines:

- A vector store: Chroma or FAISS
- BM25 retrieval
- Metadata filters for video, playlist, channel, and topic tag
- A reranker such as a cross-encoder

For a query:

1. Optionally rewrite it using the conversation summary.
2. Retrieve the top 20 candidates from vector search and BM25.
3. Merge candidates with reciprocal-rank fusion.
4. Rerank the merged candidates.
5. Keep the top 5–8 candidates.

Supported scopes:

- Single video
- Playlist
- Entire library

The default scope is the most recently discussed video unless the router or user chooses otherwise.

Whole-video summaries and notes should use map-reduce over chapter summaries rather than top-k retrieval alone.

### Citation requirements

- Every factual statement must cite `[video_id@mm:ss]`.
- Timestamp links must point to `youtu.be/<video_id>?t=<start_s>`.
- If retrieval finds no relevant content, the answer must say that the video does not appear to cover the topic rather than guess.

### 4.4 Router

The router must produce structured output:

```json
{
  "intent": "summarize",
  "confidence": 0.85,
  "reason": "The request asks for a short summary",
  "scope": "single_video",
  "params": {"length": "10 bullets"}
}
```

Supported intents:

- `summarize`
- `notes`
- `quiz`
- `qa`
- `explain`
- `plan`
- `library_query`
- `unclear`

Implement and compare three strategies behind one interface:

1. LLM classifier with structured JSON output.
2. Embedding similarity against labeled example requests.
3. Hybrid routing: embeddings first; invoke the LLM only when the top two intents are close.

Routing behavior:

- Requests below a tunable confidence threshold, initially `0.6`, go to clarification.
- Extract parameters such as length, format, question count, and study duration.
- A named video that has not yet been ingested triggers ingestion first.

### 4.5 Memory

| Tier | Contents | Storage | Lifecycle |
|---|---|---|---|
| Short-term | Current session turns | LangGraph state | Summarize past roughly 3,000 tokens |
| Semantic | Goals, topic level, format preferences, target exams/interviews | Vector store plus SQLite | Extract, deduplicate, and version after turns |
| Episodic | Studied videos, generated notes, quiz attempts, per-question results | SQLite | Append per session |
| Scheduling | Flashcard ease, interval, and due date | SQLite | Update after reviews |

Memory write policy:

- Store only durable user-stated facts and verified results.
- Examples of valid records: "preparing for GenAI interviews" and "prefers concise bullets".
- Do not store model-inferred beliefs about the user's ability level.
- Compute topic level from quiz results instead.
- On conflict, keep the new value and move the old value into history.
- "Forget X" must remove the corresponding record and embeddings.

Memory read policy:

- Load goals and preferences for every session.
- Load weak topics for quiz, notes, and study-plan generation.

Spaced repetition:

- Use an SM-2-style scheduler.
- Store ease, interval in days, and due date for every flashcard.
- A correct answer lengthens the interval.
- A miss resets the interval and tags the topic as weak.
- Provide a due-today query.

Before creating new notes, check whether a concept is already well covered in studied material. Point to the existing material rather than unnecessarily repeating it.

### 4.6 Specialist agents

#### Summarizer

Produce:

- TL;DR
- Key takeaways
- Chapter outline with timestamps

Use map-reduce over chapter summaries and support configurable length.

#### Notes writer

Produce structured study notes containing:

- Concepts
- Definitions
- Examples
- Common mistakes

Follow saved format preferences and cite timestamps.

#### Quiz maker

Generate:

- Multiple-choice questions
- Short-answer questions
- Answers
- Explanations
- Source timestamps

Requirements:

- Weight difficult topics toward weak areas.
- Every question must be answerable from the cited transcript span.
- Persist quiz attempts and per-question results.

#### Q&A

- Answer directly using hybrid retrieval.
- Respect the selected scope.
- Refuse uncovered questions instead of guessing.

#### Explainer

- Re-explain a cited passage simply.
- Include an analogy and an optional check question.
- Use only facts supported by the passage.

#### Planner

- Produce a week-by-week schedule across videos.
- Respect goals and available study hours.
- Include review sessions based on weak topics and spaced repetition.

Every specialist must:

- Have its own prompt file.
- Use a Pydantic output schema.
- Retry once or more after a schema failure.

### 4.7 Grounding check

The final validation node must:

1. Split the draft into claims.
2. Verify every claim against its cited transcript span.
3. Remove or rewrite unsupported claims once.
4. Flag claims that remain unsupported.
5. Record the grounding report: supported count, unsupported count, and citation mismatch count.
6. Save grounding results to the trace and evaluation output.

### 4.8 Security and robustness

- Wrap transcript text in delimiters and treat it as untrusted data.
- Tell the model never to follow instructions found inside transcripts.
- Handle missing captions, non-English audio, removed videos, music-only videos, and very long videos clearly.
- Use local caching and do not republish transcript content.
- Test prompt-injection attempts and off-topic requests.

## 5. Evaluation harness

The evaluation system is a required portfolio differentiator.

### 5.1 Versioned datasets

Store IDs and labels in the repository. Do not store full transcripts in Git.

| Dataset | Starting size | Contents |
|---|---:|---|
| Video gold set | 15–20 videos | 8–15 hand-written key points and 5–10 timestamped questions per video |
| Routing set | 80–100 requests | Intent labels, including ambiguous and multi-intent cases |
| Retrieval set | 60–80 questions | Expected source chunk or timestamp range |
| Quiz audit set | 40 questions | Answerability, correctness, and distractor labels |
| Memory scenarios | 15 flows | Preferences, weak topics, updates, and revision schedules |
| Adversarial set | 15 cases | Hidden instructions, bad captions, missing captions, and off-topic requests |

### 5.2 Metrics

| Area | Metrics |
|---|---|
| Summaries and notes | Coverage, faithfulness, conciseness, hallucination count |
| Citations | Citation accuracy, timestamp error, uncited-claim rate |
| Retrieval | Hit rate at k, MRR, timestamp-range overlap |
| Q&A | Reference correctness, refusal correctness |
| Quizzes | Answerability, answer correctness, distractor quality, duplicate rate, difficulty balance |
| Routing | Accuracy, precision, recall, confusion matrix, clarification rate, wrong-route rate |
| Memory | Preference recall, weak-topic detection, scheduler correctness, update and forget compliance |
| Robustness | Manual vs auto vs Whisper quality changes, missing-caption behavior, injection resistance |
| System | Latency, cost, tokens per output type |

Judge calibration:

- Use an LLM judge for coverage and faithfulness.
- Hand-label 20–30 judge decisions.
- Report human-judge agreement.
- Prefer a different model family for judging than for generation.

### 5.3 Regression gate

Store baseline metrics per Git commit.

The regression run must fail if faithfulness, coverage, citation accuracy, or routing accuracy falls below the configured margin for the current baseline.

## 6. Observability

Trace every request with Langfuse or LangSmith.

A trace must record:

- Ingestion path
- Transcript quality
- Router decision
- Retrieved chunks
- Prompts
- Grounding report
- Cost
- Output latency

Store `trace_id` with every generated output.

The UI should expose:

- Latest evaluation scores
- Metric trends
- Cost per video
- Links from outputs back to source chunks and traces

## 7. Technology stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph |
| Transcripts | `youtube-transcript-api`, `yt-dlp`, Whisper fallback |
| LLM | API model behind a common client; separate judge model |
| Retrieval | Chroma or FAISS, `rank_bm25`, cross-encoder reranker |
| Storage | SQLite for metadata, cache, memory, scheduling, and eval results |
| Schemas | Pydantic |
| Evaluation | pytest, custom scripts, RAGAS retrieval metrics |
| Tracing | Langfuse or LangSmith |
| UI | Streamlit |
| Export | Markdown and Anki using `genanki` |

## 8. Repository layout

```text
tubetutor/
├── README.md
├── pyproject.toml
├── requirements.txt
├── data/
│   ├── cache/                 # gitignored transcripts and metadata
│   └── evals/
│       ├── video_gold.yaml
│       ├── routing.jsonl
│       ├── retrieval.jsonl
│       ├── quiz_audit.jsonl
│       └── memory/*.yaml
├── src/tubetutor/
│   ├── graph.py
│   ├── state.py
│   ├── ingest/
│   │   ├── resolve.py
│   │   ├── transcript.py
│   │   ├── whisper_fallback.py
│   │   └── clean.py
│   ├── rag/
│   │   ├── chunkers.py
│   │   ├── index.py
│   │   ├── retriever.py
│   │   ├── rerank.py
│   │   └── summaries.py
│   ├── router/
│   │   ├── llm_router.py
│   │   ├── embed_router.py
│   │   └── hybrid.py
│   ├── memory/
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   ├── episodic.py
│   │   └── scheduler.py
│   ├── agents/
│   │   ├── summarizer.py
│   │   ├── notes.py
│   │   ├── quiz.py
│   │   ├── qa.py
│   │   ├── explainer.py
│   │   └── planner.py
│   ├── guardrails/
│   │   └── grounding.py
│   ├── llm/
│   │   ├── client.py
│   │   └── prompts/
│   ├── export/
│   │   ├── markdown.py
│   │   └── anki.py
│   └── app/
│       └── streamlit_app.py
├── evals/
│   ├── run_all.py
│   ├── coverage_eval.py
│   ├── citation_eval.py
│   ├── retrieval_eval.py
│   ├── quiz_eval.py
│   ├── router_eval.py
│   ├── memory_eval.py
│   └── reports/
└── tests/
```

## 9. Milestones

| # | Milestone | Deliverable | Done when |
|---:|---|---|---|
| 1 | Ingestion | Fetch, fallback, clean, cache transcripts | A video URL becomes a cached, timestamped transcript |
| 2 | Core RAG | Chunking, hybrid retrieval, cited Q&A | Retrieval dataset exists and baseline hit rate is recorded |
| 3 | Summaries and notes | Map-reduce summaries, notes writer, grounding check | Gold key points exist for 10 videos and baseline coverage/faithfulness are recorded |
| 4 | Router | Three strategies, clarification, parameter extraction | Router evaluations compare the strategies |
| 5 | Quizzes and flashcards | Quiz agent, flashcard schema, Anki export | Quiz audit is labeled and answerable rate is reported |
| 6 | Memory | Preferences, episodic log, SM-2 scheduler, weak-topic weighting | Memory scenarios pass and a second quiz targets weak topics |
| 7 | Planner and explainer | Study plans and simplified explanations | Scenario tests pass |
| 8 | Gate and polish | Regression gate, tracing, Streamlit UI, README results | One command reproduces metrics and a stranger can run the project |

Suggested pace: approximately one milestone per week for part-time work.

## 10. Experiments

1. Chapter-aware chunking versus fixed-size chunking
2. Map-reduce summaries versus top-k summaries
3. Manual, automatic, and Whisper transcript quality
4. Grounding check impact on hallucinations and latency
5. Router strategies and confidence-threshold behavior
6. Weak-topic-weighted quizzes versus uniform quizzes
7. LLM judge versus hand-labelled coverage and faithfulness
8. Requiring cited source spans versus not requiring them for quiz quality

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Poor or missing captions | Track source quality, Whisper fallback, and surface quality warnings |
| Hallucinated notes or quiz answers | Require citations, grounding checks, source-answerability checks, and refusal paths |
| Long videos exceed context limits | Chapter-level map-reduce with caps and progress reporting |
| Judge bias or unreliability | Calibration sample, different judge model family, agreement reporting |
| Copyright or terms-of-service concerns | Personal use, local cache, store IDs and labels instead of transcripts |
| Prompt injection in transcripts | Delimiters, untrusted-data instructions, and adversarial tests |
| Scope creep | Follow milestone order and defer stretch goals |

## 12. Stretch goals

- Multi-video synthesis comparing creators and disagreement detection
- Cross-video concept graph
- Browser extension or share-sheet integration
- Voice-based quiz mode
- Export to Notion or Obsidian
- Nightly due-flashcard review job

## 13. Portfolio framing

Present the project as:

> “I built an agentic learning assistant over YouTube transcripts with RAG, memory, and routing, and measured summaries, citations, and quizzes against a hand-labelled gold set using a regression gate.”

The README should lead with measured result tables and experiment findings, followed by architecture and setup instructions.

For a demo, show:

1. Ingesting a video.
2. Asking a timestamped Q&A question.
3. Generating notes or a quiz.
4. Recording quiz weakness.
5. Generating a stronger follow-up quiz.
6. Showing the trace and evaluation report.
