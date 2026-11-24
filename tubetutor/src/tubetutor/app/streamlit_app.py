"""Minimal Streamlit entry point for the TubeTutor prototype."""

from __future__ import annotations

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


if st is not None:
    st.title("TubeTutor")
    st.write("Upload a YouTube URL or playlist to begin building study material.")
    video_url = st.text_input("YouTube URL")
    if video_url:
        st.info(f"Queued: {video_url}")
else:  # pragma: no cover
    print("Streamlit is not installed. Install requirements and rerun the app.")
