"""Conservative cleanup that preserves extracted content."""

import re


def clean_text(text: str) -> str:
    """Normalize line endings, trim line edges, and collapse excess blank lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
