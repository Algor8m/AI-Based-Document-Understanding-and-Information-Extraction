import re
from typing import Any


def extract_facts(text: str) -> dict[str, Any]:
    """Extract contact details, dates, and invoice fields from document text."""
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

    # Invoice number: Invoice Number, Invoice No., Invoice #, etc.
    invoice_number_match = re.search(
        r"(?im)^\s*(?:invoice\s*(?:number|no\.?|#)|"
        r"inv(?:oice)?\s*(?:no\.?|#))"
        r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]*)",
        text,
    )

    # Invoice date: Invoice Date or Date of Invoice.
    invoice_date_match = re.search(
        r"(?im)^\s*(?:invoice\s*date|date\s+of\s+invoice)"
        r"\s*[:#-]?\s*"
        r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
    )

    # Amount due: support common invoice total labels and currencies.
    amount_due_match = re.search(
        r"(?im)^\s*(?:total\s+amount\s+due|amount\s+due|"
        r"balance\s+due|total\s+due|grand\s+total|"
        r"total\s+payable|amount\s+payable)"
        r"\s*[:=-]?\s*"
        r"(?:(?:INR|Rs\.?|₹|USD|US\$|\$)\s*)?"
        r"([\d,]+(?:\.\d{1,2})?)",
        text,
    )

    return {
        "emails": list(dict.fromkeys(emails)),
        "phone_numbers": list(dict.fromkeys(
            number.strip() for number in phone_numbers
        )),
        "dates": list(dict.fromkeys(dates)),
        "text_length": len(text),
        "invoice_number": (
            invoice_number_match.group(1)
            if invoice_number_match else None
        ),
        "invoice_date": (
            invoice_date_match.group(1)
            if invoice_date_match else None
        ),
        "amount_due": (
            amount_due_match.group(1).replace(",", "")
            if amount_due_match else None
        ),
    }