"""
enrich_sermon.py

Sends a sermon transcript + metadata to the Claude API and returns
structured enrichment data as a Python dict.

Enrichment includes:
- Primary Bible book and passage
- All scripture references
- Sermon series name
- Speaker name
- Theological tags
- Summary, outline, key points
- AI-edited transcript (grammar, paragraphs, no music)
- Vault folder path
"""

import json
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TRANSCRIPT_CHARS = 80_000  # ~20k tokens; enough for a full sermon

SYSTEM_PROMPT = """You are an expert theologian and sermon archivist for a Reformed evangelical church.
Your job is to analyze sermon transcripts and extract structured metadata for a church staff knowledge base.
Always return valid JSON. Be precise with Bible references (use full book names, not abbreviations).
For theological tags, use lowercase kebab-case (e.g., justification-by-faith, not "justification by faith").
"""

USER_PROMPT_TEMPLATE = """Analyze the following sermon and return a JSON object with these exact fields:

{{
  "primary_book": "The main Bible book this sermon is centered on (e.g., Romans). Use 'None' if purely topical.",
  "primary_passage": "The main scripture reference (e.g., Romans 8:1-17). Use 'None' if no clear passage.",
  "all_passages": ["Array of all scripture references mentioned in the sermon"],
  "series": "The sermon series name if this is part of a series (infer from title/description patterns). Use 'Standalone' if not part of a series.",
  "speaker": "The preacher's full name. Infer from transcript or description context.",
  "theological_tags": ["3-8 lowercase kebab-case theological topic tags (e.g., grace, justification, holy-spirit, prayer, suffering, discipleship, resurrection)"],
  "summary": "A 2-3 paragraph narrative summary of the sermon's main argument and application.",
  "outline": ["Array of 3-5 main point strings as the preacher structured them"],
  "key_points": ["Array of 4-6 concise theological takeaway bullets"],
  "edited_transcript": "The full sermon transcript with: corrected grammar, paragraph breaks every 4-6 sentences, spelling fixed, all music/worship song lyrics and transitions completely removed (replace with nothing, not even a placeholder). Keep all theological content intact.",
  "folder": "Vault folder path. One of: 'Old Testament/<Book>', 'New Testament/<Book>', 'Topical', 'Special Events/Christmas', 'Special Events/Easter', 'Special Events/Guest Speakers'"
}}

---
VIDEO TITLE: {title}

VIDEO DESCRIPTION:
{description}

TRANSCRIPT:
{transcript}
"""


def enrich_sermon(video: dict, transcript: str) -> dict:
    """
    Call Claude API to enrich a sermon. Returns parsed JSON dict.

    Args:
        video: dict with keys: id, title, description, upload_date, url
        transcript: cleaned plain-text transcript

    Returns:
        enrichment dict with all fields above
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    truncated = transcript[:MAX_TRANSCRIPT_CHARS]
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        truncated += "\n\n[Transcript truncated for length]"

    prompt = USER_PROMPT_TEMPLATE.format(
        title=video.get("title", ""),
        description=(video.get("description") or "")[:2000],
        transcript=truncated,
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if Claude wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)


def enrich_with_retry(video: dict, transcript: str, retries: int = 2) -> dict | None:
    """Enrich a sermon with retry on failure. Returns None if all retries fail."""
    for attempt in range(retries + 1):
        try:
            return enrich_sermon(video, transcript)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < retries:
                time.sleep(2)
        except Exception as e:
            print(f"  API error (attempt {attempt + 1}): {e}")
            if attempt < retries:
                time.sleep(5)
    return None


if __name__ == "__main__":
    import sys
    # Quick test with a sample
    sample_video = {
        "id": "test123",
        "title": "The Freedom of the Sons of God — Romans 8:14-17",
        "description": "Romans Series | Pastor John Smith | Kings Cross Church",
        "upload_date": "20231015",
        "url": "https://youtube.com/watch?v=test123",
    }
    sample_transcript = "Today we are looking at Romans chapter 8 verses 14 through 17. Paul tells us that those who are led by the Spirit of God are sons of God."
    result = enrich_with_retry(sample_video, sample_transcript)
    print(json.dumps(result, indent=2))
