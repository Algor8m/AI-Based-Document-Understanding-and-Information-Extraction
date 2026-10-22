"""Conservative cleanup that preserves extracted content, punctuation, and structure."""

import re


def clean_text(text: str) -> str:
    """Normalize line endings, trim line edges, and collapse excess blank lines while preserving punctuation and reading order."""
    if not text:
        return ""

    # Strip null bytes and non-breaking spaces
    normalized = text.replace("\x00", "").replace("\u00a0", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # Strip whitespace at the extremities of each line without altering content
    lines = [line.strip() for line in normalized.split("\n")]

    # Collapse sequences of 3 or more newlines to a standard 2-newline paragraph break
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
