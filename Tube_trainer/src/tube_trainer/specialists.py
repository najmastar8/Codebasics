"""Grounded specialist outputs for summaries, notes, quizzes, explanations, plans and recipes."""

from __future__ import annotations

import re
from collections.abc import Iterable
from math import log

from .rag import RagIndex, TranscriptChunk, RetrievedChunk, _format_timestamp

SUMMARY_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "being",
    "but", "by", "can", "could", "did", "do", "does", "for", "from", "had",
    "has", "have", "he", "her", "hers", "him", "his", "how", "i", "if", "in",
    "into", "is", "it", "its", "may", "might", "of", "on", "or", "our", "she",
    "should", "so", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "to", "was", "we", "were",
    "what", "when", "where", "which", "who", "will", "with", "would", "you",
    "your",
}


def _citation(chunk: TranscriptChunk | RetrievedChunk) -> str:
    return _citation_at(chunk.video_id, chunk.start_s)


def _citation_at(video_id: str, start_s: float) -> str:
    timestamp = int(start_s)
    return f"[{video_id}@{_format_timestamp(start_s)}](https://youtu.be/{video_id}?t={timestamp})"


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


def _content_words(sentence: str) -> list[str]:
    return [
        word.casefold()
        for word in re.findall(r"\b[\w'-]+\b", sentence)
        if len(word) > 2 and word.casefold() not in SUMMARY_STOP_WORDS
    ]


def _summary_candidates(
    chunks: Iterable[TranscriptChunk],
) -> list[tuple[str, TranscriptChunk, list[str]]]:
    candidates: list[tuple[str, TranscriptChunk, list[str]]] = []
    seen: set[str] = set()
    for chunk in chunks:
        for sentence in _sentences(chunk.text):
            normalized = sentence.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            words = _content_words(sentence)
            sentence_word_count = len(re.findall(r"\b[\w'-]+\b", sentence))
            if len(words) < 3 or sentence_word_count < 6 or sentence_word_count > 40:
                continue
            if re.match(
                r"^(and|but|so|because|also|anyway|like|subscribe|thank you)\b",
                sentence,
                re.IGNORECASE,
            ):
                continue
            candidates.append((sentence, chunk, words))
    return candidates


def _rank_summary_candidates(
    candidates: list[tuple[str, TranscriptChunk, list[str]]],
    count: int,
) -> list[tuple[str, TranscriptChunk]]:
    if not candidates:
        return []

    document_frequency: dict[str, int] = {}
    for _, _, words in candidates:
        for word in set(words):
            document_frequency[word] = document_frequency.get(word, 0) + 1

    scored: list[tuple[float, int, str, TranscriptChunk, set[str]]] = []
    for index, (sentence, chunk, words) in enumerate(candidates):
        unique_words = set(words)
        salience = sum(
            log(1 + len(candidates) / document_frequency[word])
            for word in unique_words
        )
        length_penalty = len(words) ** 0.5
        specificity_bonus = min(len(unique_words), 8) * 0.15
        score = salience / length_penalty + specificity_bonus
        scored.append((score, index, sentence, chunk, unique_words))

    selected: list[tuple[str, TranscriptChunk, set[str]]] = []
    used_chapters: set[str] = set()
    while scored and len(selected) < count:
        best_index = max(
            range(len(scored)),
            key=lambda index: (
                scored[index][0]
                - max(
                    (
                        len(scored[index][4] & prior_words)
                        / max(len(scored[index][4] | prior_words), 1)
                        for _, _, prior_words in selected
                    ),
                    default=0.0,
                )
                * 1.5
                + (0.25 if scored[index][3].chapter_title not in used_chapters else 0.0),
                -scored[index][1],
            ),
        )
        _, _, sentence, chunk, words = scored.pop(best_index)
        selected.append((sentence, chunk, words))
        used_chapters.add(chunk.chapter_title)

    return [(sentence, chunk) for sentence, chunk, _ in sorted(selected, key=lambda item: item[1].start_s)]


def summarize(rag: RagIndex, video_ids: list[str], count: int = 10) -> str:
    if count <= 0:
        raise ValueError("count must be greater than zero")

    lines = ["## Key points"]
    for video_id in video_ids:
        selected = _rank_summary_candidates(
            _summary_candidates(rag.get_chunks(video_id)),
            count,
        )
        if selected:
            lines.append(f"**Video {video_id}**")
            for sentence, chunk in selected:
                lines.append(f"- {sentence} {_citation(chunk)}")
    return "\n".join(lines) if len(lines) > 1 else "The indexed transcript has no complete, specific sentences to summarize."


def make_notes(rag: RagIndex, video_ids: list[str], topic: str = "") -> str:
    query = topic if topic else "photosynthesis plants sunlight chlorophyll basketball concept"
    chunks = rag.retrieve(query, top_k=8, video_ids=video_ids)
    if not chunks:
        return "The transcript does not appear to contain enough evidence for study notes."

    lines = ["## Study notes", "### Concepts"]
    for chunk in chunks:
        lines.append(f"- {chunk.text} {_citation(chunk)}")
    lines += ["", "### Review prompts", "- Which concept in these notes should you explain in your own words?"]
    return "\n".join(lines)


def make_quiz(rag: RagIndex, video_ids: list[str], count: int = 5) -> str:
    if count <= 0:
        raise ValueError("count must be greater than zero")

    action_lemmas = {
        "uses": "use", "requires": "require", "contains": "contain",
        "produces": "produce", "creates": "create", "converts": "convert",
        "turns": "turn", "stores": "store", "provides": "provide",
        "causes": "cause", "increases": "increase", "decreases": "decrease",
        "reduces": "reduce", "improves": "improve", "supports": "support",
        "explains": "explain", "measures": "measure", "controls": "control",
        "includes": "include", "allows": "allow", "enables": "enable",
    }
    action_pattern = re.compile(
        r"^(?P<subject>[^.!?;]{2,100}?)\s+"
        r"(?P<verb>use|uses|require|requires|contain|contains|produce|produces|"
        r"create|creates|convert|converts|turn|turns|store|stores|provide|provides|"
        r"cause|causes|increase|increases|decrease|decreases|reduce|reduces|"
        r"improve|improves|support|supports|explain|explains|measure|measures|"
        r"control|controls|include|includes|allow|allows|enable|enables)\s+"
        r"(?P<object>[^.!?]+)[.!?]?$",
        re.IGNORECASE,
    )
    copula_pattern = re.compile(
        r"^(?P<subject>[^.!?;]{2,100}?)\s+(?P<verb>is|are|was|were)\s+"
        r"(?P<predicate>[^.!?]+)[.!?]?$",
        re.IGNORECASE,
    )
    cause_pattern = re.compile(
        r"^(?P<cause>[^.!?;]{3,100}?)\s+"
        r"(?P<connector>because|therefore|thus|so|which causes?|which leads to)\s+"
        r"(?P<effect>[^.!?]+)[.!?]?$",
        re.IGNORECASE,
    )

    questions: list[tuple[str, str, TranscriptChunk]] = []
    seen_questions: set[str] = set()
    seen_facts: set[str] = set()
    for video_id in video_ids:
        for chunk in rag.get_chunks(video_id):
            for sentence in _sentences(chunk.text):
                action = action_pattern.match(sentence)
                copula = copula_pattern.match(sentence)
                cause = cause_pattern.match(sentence)
                if copula:
                    subject = copula.group("subject").strip(" ,")
                    subject = subject[:1].lower() + subject[1:]
                    question = f"What {copula.group('verb').lower()} {subject}?"
                    answer = copula.group("predicate").strip(" ,")
                elif action:
                    subject = action.group("subject").strip(" ,")
                    subject = subject[:1].lower() + subject[1:]
                    verb = action.group("verb").lower()
                    object_text = action.group("object").strip(" ,")
                    lemma = action_lemmas.get(verb, verb)
                    helper = "does" if verb.endswith("s") else "do"
                    if " into " in object_text and lemma in {"convert", "turn"}:
                        source, answer = re.split(r"\s+into\s+", object_text, maxsplit=1, flags=re.IGNORECASE)
                        question = f"What {helper} {subject} {lemma} {source.strip()} into?"
                    else:
                        question = f"What {helper} {subject} {lemma}?"
                        answer = object_text
                elif cause:
                    cause_text = cause.group("cause").strip(" ,")
                    connector = cause.group("connector").lower()
                    effect = cause.group("effect").strip(" ,")
                    if connector.startswith("which"):
                        question = f"What does {cause_text} lead to?"
                        answer = effect
                    elif connector == "because":
                        question = f"Why does this happen: {cause_text}?"
                        answer = effect
                    else:
                        question = f"What happens as a result of {cause_text}?"
                        answer = effect
                else:
                    continue

                answer = answer.strip().rstrip(".!?")
                if (
                    not answer
                    or len(answer) > 180
                    or len(question) > 180
                    or len(question.split()) < 3
                ):
                    continue
                normalized = question.casefold()
                fact_key = re.sub(r"\W+", " ", f"{question} {answer}").casefold().strip()
                if normalized not in seen_questions and fact_key not in seen_facts:
                    questions.append((question, answer, chunk))
                    seen_questions.add(normalized)
                    seen_facts.add(fact_key)
                if len(questions) >= count:
                    break
            if len(questions) >= count:
                break
        if len(questions) >= count:
            break

    if not questions:
        return "The transcript does not contain clear factual sentences that can be turned into precise quiz questions."

    lines = ["## Quiz"]
    for number, (question, answer, chunk) in enumerate(questions, start=1):
        lines.append(f"{number}. {question}")
        lines.append(f"   Answer: **{answer}**")
        lines.append(f"   Source: {_citation(chunk)}")
    return "\n".join(lines)


def explain(rag: RagIndex, video_ids: list[str], question: str) -> str:
    chunks = rag.retrieve(question, top_k=3, video_ids=video_ids)
    if not chunks:
        return "The transcript does not appear to cover that topic."
    lines = ["## Simple explanation"]
    for chunk in chunks:
        lines.append(f"- In simple terms: {chunk.text}")
        lines.append(f"  Source: {_citation(chunk)}")
    lines += ["", "**Check:** Can you explain the cited passage without looking at it?"]
    return "\n".join(lines)


def make_plan(rag: RagIndex, video_ids: list[str], weeks: int = 1) -> str:
    weeks = max(1, min(weeks, 12))
    lines = ["## Study plan"]
    per_video = max(1, len(video_ids))
    for week in range(1, weeks + 1):
        video = video_ids[(week - 1) % per_video]
        summary = rag.get_summary(video) or "Review the indexed transcript passages."
        lines.append(f"### Week {week}")
        lines.append(f"- Study video {video}: {summary[:220]}")
        lines.append("- 2 x 45-minute focused sessions")
        lines.append("- 1 x 20-minute recall review using retrieved passages")
    return "\n".join(lines)


_RECIPE_ACTION = re.compile(
    r"\b(add|mix|stir|combine|pour|heat|preheat|chop|dice|slice|peel|"
    r"season|marinate|whisk|fold|knead|roll|place|transfer|cover|rest|"
    r"simmer|boil|fry|saute|sauté|sear|grill|roast|bake|broil|steam|"
    r"cook|serve|remove|drain|cool|garnish|blend|melt|spread|press)\b",
    re.IGNORECASE,
)


def make_recipe(rag: RagIndex, video_ids: list[str]) -> str:
    """Format transcript cooking steps as a simple, timestamp-linked recipe."""
    if not video_ids:
        return "Add and index a YouTube video before extracting a recipe."

    recipes: list[str] = []
    for video_id in video_ids:
        chunks = rag.get_chunks(video_id)
        transcript_segments = rag.get_transcript_segments(video_id)
        source_sentences = [
            (sentence, segment.start_s)
            for segment in transcript_segments
            for sentence in _sentences(segment.text)
        ]
        if not source_sentences:
            source_sentences = [
                (sentence, chunk.start_s)
                for chunk in chunks
                for sentence in _sentences(chunk.text)
            ]

        instructions: list[tuple[str, float]] = []
        seen: set[tuple[str, str]] = set()

        for sentence, start_s in source_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            normalized = sentence.casefold()
            key = (normalized, video_id)
            if key in seen:
                continue
            seen.add(key)

            if _RECIPE_ACTION.search(sentence):
                instructions.append((sentence, start_s))

        if not instructions:
            continue

        lines = [f"## Recipe from video {video_id}"]
        lines.extend(
            f"{number}. {text} {_citation_at(video_id, start_s)}"
            for number, (text, start_s) in enumerate(instructions, start=1)
        )
        recipes.append("\n".join(lines))

    if not recipes:
        return (
            "I couldn't identify clear ingredients or cooking steps in the "
            "indexed transcript. Try a video with spoken recipe details."
        )
    return "\n\n---\n\n".join(recipes)
