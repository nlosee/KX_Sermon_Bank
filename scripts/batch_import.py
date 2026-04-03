"""
batch_import.py

Main script to batch-import all historical Kings Cross Church sermons.

Workflow for each unprocessed video:
  1. Download auto-captions via yt-dlp
  2. Parse VTT to clean text
  3. Enrich with Claude API
  4. Write Obsidian note to vault
  5. Mark as processed (idempotent)

Run with:
  python scripts/batch_import.py

Optional flags:
  --limit N     Process only N sermons (useful for testing)
  --video-id ID Process a single video by ID
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_FILE = DATA_DIR / "videos.json"
PROCESSED_FILE = DATA_DIR / "processed.json"
NO_CAPTIONS_FILE = DATA_DIR / "no_captions.json"
LOG_FILE = DATA_DIR / "import.log"

DELAY_BETWEEN_SERMONS = 1.5  # seconds between API calls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def load_json(path: Path, default) -> dict | list:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_video(video: dict) -> str:
    """
    Process a single video through the full pipeline.

    Returns:
        "ok"          — success
        "no_captions" — captions unavailable
        "error"       — processing failed
    """
    from parse_captions import get_transcript
    from enrich_sermon import enrich_with_retry
    from create_note import write_note

    video_id = video["id"]
    title = video.get("title", video_id)
    log.info(f"Processing: {title} ({video_id})")

    # Step 1 & 2: Download and parse captions
    transcript = get_transcript(video_id, video["url"])
    if transcript is None:
        log.warning(f"  No captions available: {video_id}")
        return "no_captions"

    log.info(f"  Transcript: {len(transcript)} chars")

    # Step 3: Enrich with Claude
    enrichment = enrich_with_retry(video, transcript)
    if enrichment is None:
        log.error(f"  Enrichment failed after retries: {video_id}")
        return "error"

    log.info(f"  Enriched: folder={enrichment.get('folder')}, passage={enrichment.get('primary_passage')}")

    # Step 4: Write note
    note_path = write_note(video, enrichment, transcript)
    log.info(f"  Note written: {note_path}")

    return "ok"


def main():
    parser = argparse.ArgumentParser(description="Batch import Kings Cross Church sermons")
    parser.add_argument("--limit", type=int, default=None, help="Process only N videos")
    parser.add_argument("--video-id", type=str, default=None, help="Process a single video by ID")
    args = parser.parse_args()

    # Load video index
    if not VIDEOS_FILE.exists():
        log.error(f"videos.json not found. Run fetch_channel.py first.")
        sys.exit(1)

    all_videos: list[dict] = load_json(VIDEOS_FILE, [])
    processed: dict = load_json(PROCESSED_FILE, {})
    no_captions: list = load_json(NO_CAPTIONS_FILE, [])

    # Filter to target videos
    if args.video_id:
        videos = [v for v in all_videos if v["id"] == args.video_id]
        if not videos:
            log.error(f"Video ID not found: {args.video_id}")
            sys.exit(1)
    else:
        videos = [v for v in all_videos if v["id"] not in processed]
        log.info(f"Total videos: {len(all_videos)}  |  Already processed: {len(processed)}  |  To process: {len(videos)}")

    if args.limit:
        videos = videos[:args.limit]
        log.info(f"Limiting to {args.limit} videos")

    counts = {"ok": 0, "no_captions": 0, "error": 0}

    for i, video in enumerate(videos, 1):
        log.info(f"\n[{i}/{len(videos)}] ---")
        try:
            status = process_video(video)
        except Exception as e:
            log.exception(f"  Unexpected error: {e}")
            status = "error"

        counts[status] += 1

        if status == "ok":
            processed[video["id"]] = {
                "title": video.get("title"),
                "date": video.get("upload_date"),
            }
            save_json(PROCESSED_FILE, processed)

        elif status == "no_captions":
            if video["id"] not in no_captions:
                no_captions.append(video["id"])
                save_json(NO_CAPTIONS_FILE, no_captions)

        if i < len(videos):
            time.sleep(DELAY_BETWEEN_SERMONS)

    log.info(f"\n=== Batch import complete ===")
    log.info(f"  Success:     {counts['ok']}")
    log.info(f"  No captions: {counts['no_captions']}")
    log.info(f"  Errors:      {counts['error']}")


if __name__ == "__main__":
    # Ensure scripts/ is on the path for sibling imports
    sys.path.insert(0, str(Path(__file__).parent))
    main()
