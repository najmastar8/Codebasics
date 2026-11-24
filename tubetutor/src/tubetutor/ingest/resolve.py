from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def resolve_video_id(value: str) -> str:
    """Extract a YouTube video ID from a URL or return a bare ID."""
    value = value.strip()
    if _VIDEO_ID_RE.match(value):
        return value

    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith("/shorts/"):
            candidate = parsed.path.split("/")[2]
        elif parsed.path.startswith("/embed/"):
            candidate = parsed.path.split("/")[2]
        elif parsed.path.startswith("/live/"):
            candidate = parsed.path.split("/")[2]
        else:
            candidate = ""
    else:
        candidate = ""

    if not _VIDEO_ID_RE.match(candidate):
        raise ValueError(f"Not a valid YouTube video URL or ID: {value}")
    return candidate


def resolve_playlist_id(value: str) -> str:
    """Extract a playlist ID from a YouTube playlist URL or bare ID."""
    value = value.strip()
    parsed = urlparse(value)
    candidate = parse_qs(parsed.query).get("list", [""])[0]
    if not candidate:
        candidate = value
    if not candidate or not re.fullmatch(r"[A-Za-z0-9_-]+", candidate):
        raise ValueError(f"Not a valid YouTube playlist URL or ID: {value}")
    return candidate


def expand_playlist(value: str) -> list[str]:
    """Expand a playlist URL using yt-dlp metadata, without downloading media."""
    import yt_dlp

    options = {"extract_flat": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(value, download=False)

    entries = info.get("entries") or []
    video_ids: list[str] = []
    for entry in entries:
        if not entry:
            continue
        candidate = entry.get("id")
        if candidate:
            video_ids.append(candidate)
    return video_ids
