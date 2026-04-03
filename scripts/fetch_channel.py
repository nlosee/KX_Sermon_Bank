"""
fetch_channel.py

Downloads all video metadata from the Kings Cross Church YouTube channel
(Live streams tab) using yt-dlp (no API key required). Saves results to data/videos.json.

Filters out:
- Videos shorter than 10 minutes (Shorts, clips, promos)
- Videos uploaded before October 2021 (before livestreams began)
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CHANNEL_URL = "https://www.youtube.com/@kingscrosschurch2515/streams"
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "videos.json"

MIN_DURATION_SECONDS = 600       # 10 minutes
EARLIEST_DATE = "20211001"       # October 2021


def fetch_channel_videos() -> list[dict]:
    print(f"Fetching video list from: {CHANNEL_URL}")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        CHANNEL_URL,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    videos = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    print(f"  Found {len(videos)} total entries on channel")
    return videos


def filter_videos(videos: list[dict]) -> list[dict]:
    filtered = []
    for v in videos:
        duration = v.get("duration") or 0
        upload_date = v.get("upload_date") or ""

        if duration < MIN_DURATION_SECONDS:
            continue
        if upload_date and upload_date < EARLIEST_DATE:
            continue

        filtered.append({
            "id": v.get("id"),
            "title": v.get("title"),
            "upload_date": upload_date,
            "description": v.get("description") or "",
            "duration": duration,
            "url": v.get("url") or f"https://www.youtube.com/watch?v={v.get('id')}",
        })

    return filtered


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_videos = fetch_channel_videos()
    videos = filter_videos(raw_videos)

    print(f"  After filtering: {len(videos)} sermon-length videos")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    print(f"  Saved to {OUTPUT_FILE}")
    return videos


if __name__ == "__main__":
    main()
