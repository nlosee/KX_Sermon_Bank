"""
sync.py

Weekly sync script: checks the YouTube channel for new sermon uploads
and processes any that haven't been imported yet.

Designed to run as a GitHub Action on a cron schedule.
Safe to run manually at any time — already-processed videos are skipped.

Run with:
  python scripts/sync.py
"""

import json
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add scripts/ to path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

from fetch_channel import fetch_channel_videos, filter_videos
from parse_captions import get_transcript
from enrich_sermon import enrich_with_retry
from create_note import write_note

DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_FILE = DATA_DIR / "videos.json"
PROCESSED_FILE = DATA_DIR / "processed.json"
NO_CAPTIONS_FILE = DATA_DIR / "no_captions.json"
LOG_FILE = DATA_DIR / "sync.log"

DELAY_BETWEEN_SERMONS = 2.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def load_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    log.info("=== KX Sermon Bank Sync ===")

    # Refresh video list from YouTube
    log.info("Fetching latest video list from channel...")
    raw_videos = fetch_channel_videos()
    videos = filter_videos(raw_videos)

    # Save updated video index
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_json(VIDEOS_FILE, videos)
    log.info(f"Channel has {len(videos)} sermon-length videos")

    # Find new videos
    processed: dict = load_json(PROCESSED_FILE, {})
    no_captions: list = load_json(NO_CAPTIONS_FILE, [])

    new_videos = [v for v in videos if v["id"] not in processed and v["id"] not in no_captions]
    log.info(f"New videos to process: {len(new_videos)}")

    if not new_videos:
        log.info("Nothing to do. All sermons are up to date.")
        return

    counts = {"ok": 0, "no_captions": 0, "error": 0}

    for i, video in enumerate(new_videos, 1):
        video_id = video["id"]
        title = video.get("title", video_id)
        log.info(f"\n[{i}/{len(new_videos)}] {title}")

        try:
            transcript = get_transcript(video_id, video["url"])
            if transcript is None:
                log.warning(f"  No captions for {video_id}")
                no_captions.append(video_id)
                save_json(NO_CAPTIONS_FILE, no_captions)
                counts["no_captions"] += 1
                continue

            enrichment = enrich_with_retry(video, transcript)
            if enrichment is None:
                log.error(f"  Enrichment failed: {video_id}")
                counts["error"] += 1
                continue

            note_path = write_note(video, enrichment, transcript)
            log.info(f"  Note written: {note_path}")

            processed[video_id] = {
                "title": video.get("title"),
                "date": video.get("upload_date"),
            }
            save_json(PROCESSED_FILE, processed)
            counts["ok"] += 1

        except Exception as e:
            log.exception(f"  Unexpected error: {e}")
            counts["error"] += 1

        if i < len(new_videos):
            time.sleep(DELAY_BETWEEN_SERMONS)

    log.info(f"\n=== Sync complete ===")
    log.info(f"  New notes added: {counts['ok']}")
    log.info(f"  No captions:     {counts['no_captions']}")
    log.info(f"  Errors:          {counts['error']}")


if __name__ == "__main__":
    main()
