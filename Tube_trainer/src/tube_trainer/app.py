"""Streamlit interface for YouTube Recipe Writer."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tube_trainer.ingest import IngestionPipeline
    from tube_trainer.rag import RagIndex
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
else:
    from .ingest import IngestionPipeline
    from .rag import RagIndex
    from .router import route_request
    from .specialists import (
        explain,
        make_notes,
        make_plan,
        make_quiz,
        make_recipe,
        summarize,
    )
    from .trace import TraceStore

import streamlit as st


DATA_DIR = Path(__file__).resolve().parents[2] / "data"

st.set_page_config(page_title="YouTube Recipe Writer", page_icon="🍳", layout="wide")
st.title("YouTube Recipe Writer")
st.caption("Turn YouTube cooking videos into timestamp-linked recipes")

pipeline = IngestionPipeline(DATA_DIR)
index = RagIndex(DATA_DIR)
traces = TraceStore(DATA_DIR)

url = st.text_input("YouTube video or playlist URL")
if st.button("Ingest") and url:
    with st.spinner("Resolving and ingesting transcript..."):
        try:
            ids = pipeline.resolve_playlist_video_ids(url)
            if ids:
                records = [pipeline.ingest(f"https://youtu.be/{video_id}") for video_id in ids]
            else:
                records = [pipeline.ingest(url)]
            for record in records:
                index.index_record(record)
            st.session_state["video_ids"] = [record.video_id for record in records]
            st.success(f"Indexed {len(records)} video(s).")
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

video_ids = st.session_state.get("video_ids", [])
if st.button("Extract recipe from indexed video"):
    st.markdown(make_recipe(index, video_ids))

request = st.text_input("What would you like to learn?")

if st.button("Generate") and request:
    route = route_request(request)
    if route.confidence < 0.6:
        output = "Please clarify: recipe, summary, study notes, quiz, explanation, plan, or transcript question."
    elif route.intent == "summarize":
        output = summarize(index, video_ids, int(route.params.get("count", 10)))
    elif route.intent == "notes":
        output = make_notes(index, video_ids, request)
    elif route.intent == "quiz":
        output = make_quiz(index, video_ids, int(route.params.get("count", 5)))
    elif route.intent == "explain":
        output = explain(index, video_ids, request)
    elif route.intent == "plan":
        output = make_plan(index, video_ids, int(route.params.get("weeks", 1)))
    elif route.intent == "recipe":
        output = make_recipe(index, video_ids)
    else:
        output = index.answer(request, video_ids=video_ids or None)
    st.markdown(output)
    traces.write(request, video_ids, route.intent, [])
