"""
parse_captions.py

Downloads auto-generated YouTube captions for a video using yt-dlp,
then parses the VTT file into clean plain text.

VTT quirks handled:
- Strips WEBVTT header and cue timestamps
- Deduplicates overlapping caption lines (YouTube repeats lines across cues)
- Joins lines into readable paragraphs
"""

import re
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CAPTIONS_DIR = DATA_DIR / "captions"


def download_captions(video_id: str, video_url: str) -> Path | None:
    """Download auto-generated English captions for a video. Returns VTT path or None."""
    CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    output_template = str(CAPTIONS_DIR / video_id)

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--skip-download",
        "--no-warnings",
        "-o", output_template,
        video_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    vtt_path = CAPTIONS_DIR / f"{video_id}.en.vtt"
    if vtt_path.exists():
        return vtt_path

    # yt-dlp sometimes writes with a slightly different name pattern
    for f in CAPTIONS_DIR.glob(f"{video_id}*.vtt"):
        return f

    print(f"  WARNING: No captions found for {video_id}", file=sys.stderr)
    return None


def parse_vtt(vtt_path: Path) -> str:
    """Parse a VTT file into clean plain text, deduplicating overlapping lines."""
    text = vtt_path.read_text(encoding="utf-8")

    # Split into cue blocks (separated by blank lines)
    blocks = re.split(r"\n\s*\n", text)

    seen_lines: list[str] = []
    for block in blocks:
        lines = block.strip().splitlines()
        for line in lines:
            line = line.strip()
            # Skip WEBVTT header, NOTE blocks, timestamps, cue identifiers
            if not line:
                continue
            if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+", line):
                continue
            if re.match(r"^\d+$", line):
                continue

            # Strip VTT inline tags like <00:00:00.000>, <c>, </c>
            line = re.sub(r"<[^>]+>", "", line).strip()
            if not line:
                continue

            # Deduplicate: skip if identical to the last seen line
            if seen_lines and seen_lines[-1] == line:
                continue

            seen_lines.append(line)

    # Join into a single text block, then break into paragraphs every ~5 sentences
    raw_text = " ".join(seen_lines)
    return _add_paragraph_breaks(raw_text)


def _add_paragraph_breaks(text: str, sentences_per_paragraph: int = 5) -> str:
    """Split a long text string into paragraphs every N sentences."""
    # Split on sentence-ending punctuation followed by space and capital letter
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    paragraphs = []
    for i in range(0, len(sentences), sentences_per_paragraph):
        chunk = " ".join(sentences[i:i + sentences_per_paragraph])
        paragraphs.append(chunk)
    return "\n\n".join(paragraphs)


def get_transcript(video_id: str, video_url: str) -> str | None:
    """High-level helper: download captions and return parsed text. Returns None if unavailable."""
    vtt_path = download_captions(video_id, video_url)
    if vtt_path is None:
        return None
    return parse_vtt(vtt_path)


if __name__ == "__main__":
    # Quick test: python parse_captions.py <video_id> <url>
    if len(sys.argv) < 3:
        print("Usage: python parse_captions.py <video_id> <youtube_url>")
        sys.exit(1)
    vid_id, url = sys.argv[1], sys.argv[2]
    transcript = get_transcript(vid_id, url)
    if transcript:
        print(transcript[:2000])
    else:
        print("No transcript available.")
