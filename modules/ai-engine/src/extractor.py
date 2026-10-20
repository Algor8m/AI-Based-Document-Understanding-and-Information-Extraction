
import re
from typing import Any


def extract_facts(text: str) -> dict[str, Any]:
    """
    Extract basic facts from document text.

    This initial version uses regular expressions.
    It does not yet perform advanced semantic extraction.
    """

    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")

    emails = re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text,
    )


    phone_numbers = re.findall(
        r"(?<!\w)\+?\d{1,3}(?:[\s().-]*\d){9,12}(?!\w)",
        text,
    )


    dates = re.findall(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{4}-\d{2}-\d{2})\b",
        text,
    )

    return {
        "emails": list(dict.fromkeys(emails)),
        "phone_numbers": list(dict.fromkeys(
            number.strip() for number in phone_numbers
        )),
        "dates": list(dict.fromkeys(dates)),
        "text_length": len(text),
    }
