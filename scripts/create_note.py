"""
create_note.py

Renders an Obsidian markdown note from enriched sermon data and writes it
to the correct vault folder, creating subdirectories as needed.
"""

import re
from datetime import datetime
from pathlib import Path

VAULT_DIR = Path(__file__).parent.parent / "vault"


def _safe_filename(title: str) -> str:
    """Convert a sermon title to a safe filename (no special chars)."""
    # Replace characters not allowed in filenames
    safe = re.sub(r'[\\/:*?"<>|]', "", title)
    safe = safe.strip()
    return safe[:120]  # Cap length


def _format_date(upload_date: str) -> str:
    """Convert yt-dlp date string YYYYMMDD to YYYY-MM-DD."""
    if not upload_date or len(upload_date) < 8:
        return upload_date or "Unknown"
    try:
        return datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return upload_date


def _format_tags_yaml(theological_tags: list, bible_book: str, testament: str) -> str:
    """Build the YAML tags list."""
    tags = list(theological_tags) if theological_tags else []
    if bible_book and bible_book.lower() != "none":
        book_tag = f"{testament}/{bible_book.replace(' ', '-')}"
        if book_tag not in tags:
            tags.append(book_tag)
    lines = "\n".join(f'  - "{t}"' for t in tags)
    return lines


def _get_testament(folder: str) -> str:
    """Infer Old/New Testament from folder path."""
    if folder.startswith("Old Testament"):
        return "Old-Testament"
    if folder.startswith("New Testament"):
        return "New-Testament"
    return "Topical"


def _indent_block(text: str, indent: str = "> ") -> str:
    """Indent each line for Obsidian callout blocks."""
    return "\n".join(indent + line if line.strip() else ">" for line in text.splitlines())


def render_note(video: dict, enrichment: dict, raw_transcript: str) -> str:
    """
    Build the full Obsidian markdown note string.

    Args:
        video: raw metadata from yt-dlp (id, title, upload_date, url, duration)
        enrichment: structured data from Claude API
        raw_transcript: cleaned plain-text transcript (pre-AI edit)

    Returns:
        Full markdown string for the note
    """
    date_str = _format_date(video.get("upload_date", ""))
    title = video.get("title", "Untitled")
    folder = enrichment.get("folder", "Topical")
    testament = _get_testament(folder)
    bible_book = enrichment.get("primary_book", "")
    if bible_book and bible_book.lower() == "none":
        bible_book = ""

    duration_min = round((video.get("duration") or 0) / 60)

    all_passages = enrichment.get("all_passages") or []
    passages_list = "\n".join(f"- {p}" for p in all_passages) if all_passages else "- (none identified)"

    outline = enrichment.get("outline") or []
    outline_text = "\n".join(f"{i+1}. {point}" for i, point in enumerate(outline))

    key_points = enrichment.get("key_points") or []
    key_points_text = "\n".join(f"- {kp}" for kp in key_points)

    tags_yaml = _format_tags_yaml(
        enrichment.get("theological_tags", []),
        bible_book,
        testament,
    )

    edited_transcript = enrichment.get("edited_transcript") or raw_transcript
    raw_indented = _indent_block(raw_transcript)
    edited_indented = _indent_block(edited_transcript)

    speaker = enrichment.get("speaker") or "Unknown"
    series = enrichment.get("series") or "Standalone"
    passage = enrichment.get("primary_passage") or ""
    if passage and passage.lower() == "none":
        passage = ""

    note = f"""---
title: "{title}"
date: {date_str}
speaker: "{speaker}"
series: "{series}"
bible_book: "{bible_book}"
passage: "{passage}"
all_passages:
{chr(10).join(f'  - "{p}"' for p in all_passages)}
youtube_url: "{video.get('url', '')}"
duration_min: {duration_min}
tags:
{tags_yaml}
status: processed
---

## Summary

{enrichment.get('summary', '')}

## Outline

{outline_text}

## Key Theological Points

{key_points_text}

## Scripture References

{passages_list}

> [!note]- Edited Transcript
{edited_indented}

> [!note]- Raw Transcript
{raw_indented}
"""
    return note


def write_note(video: dict, enrichment: dict, raw_transcript: str) -> Path:
    """
    Write the sermon note to the vault. Creates directories as needed.

    Returns:
        Path to the written file
    """
    date_str = _format_date(video.get("upload_date", ""))
    title = _safe_filename(video.get("title", "Untitled"))
    folder = enrichment.get("folder", "Topical")

    note_dir = VAULT_DIR / folder
    note_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{date_str} - {title}.md"
    note_path = note_dir / filename

    content = render_note(video, enrichment, raw_transcript)
    note_path.write_text(content, encoding="utf-8")

    return note_path


if __name__ == "__main__":
    # Quick test
    sample_video = {
        "id": "abc123",
        "title": "Walking in the Spirit — Romans 8:14-17",
        "upload_date": "20231015",
        "url": "https://youtube.com/watch?v=abc123",
        "duration": 2700,
    }
    sample_enrichment = {
        "primary_book": "Romans",
        "primary_passage": "Romans 8:14-17",
        "all_passages": ["Romans 8:14-17", "Galatians 4:6"],
        "series": "Romans: The Gospel Unleashed",
        "speaker": "John Smith",
        "theological_tags": ["holy-spirit", "adoption", "sanctification"],
        "summary": "Pastor John walks through Paul's teaching on the Spirit of adoption...",
        "outline": ["The Spirit of Slavery vs. Spirit of Adoption", "Crying Abba Father", "Heirs with Christ"],
        "key_points": ["The Spirit assures believers of their sonship", "Adoption is not earned but given"],
        "edited_transcript": "Today we are in Romans chapter 8...",
        "folder": "New Testament/Romans",
    }
    path = write_note(sample_video, sample_enrichment, "Raw transcript text here...")
    print(f"Note written to: {path}")
