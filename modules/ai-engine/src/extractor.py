"""Structured entity extraction for invoices, agreements, and general documents with evidence capture."""

import re
from typing import Any


def extract_facts(text: str) -> dict[str, Any]:
    """Extract contact details, dates, invoice fields, and contract terms from document text.

    Preserves source evidence snippets for each detected field.
    Never fabricates facts; missing values are explicitly set to None or empty lists.
    """
    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")

    field_evidence: dict[str, Any] = {}

    # Email extraction
    emails = re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text,
    )
    unique_emails = list(dict.fromkeys(emails))
    if unique_emails:
        field_evidence["emails"] = unique_emails

    # Phone numbers
    phone_numbers = re.findall(
        r"(?<!\w)\+?\d{1,3}(?:[\s().-]*\d){9,12}(?!\w)",
        text,
    )
    unique_phones = list(dict.fromkeys(number.strip() for number in phone_numbers))
    if unique_phones:
        field_evidence["phone_numbers"] = unique_phones

    # Dates
    dates = re.findall(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b",
        text,
    )
    unique_dates = list(dict.fromkeys(dates))
    if unique_dates:
        field_evidence["dates"] = unique_dates

    # Invoice number: Invoice Number, Invoice No., Invoice #, Inv No., etc.
    invoice_number_match = re.search(
        r"(?im)^\s*(?:invoice\s*(?:number|no\.?|#)|inv(?:oice)?\s*(?:no\.?|#))\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]*)",
        text,
    )
    invoice_number = None
    if invoice_number_match:
        invoice_number = invoice_number_match.group(1).strip()
        field_evidence["invoice_number"] = invoice_number_match.group(0).strip()

    # Invoice date: Invoice Date or Date of Invoice
    invoice_date_match = re.search(
        r"(?im)^\s*(?:invoice\s*date|date\s+of\s+invoice)\s*[:#-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
    )
    invoice_date = None
    if invoice_date_match:
        invoice_date = invoice_date_match.group(1).strip()
        field_evidence["invoice_date"] = invoice_date_match.group(0).strip()

    # Amount due: support common invoice total labels and currencies
    amount_due_match = re.search(
        r"(?im)^\s*(?:total\s+amount\s+due|amount\s+due|balance\s+due|total\s+due|grand\s+total|total\s+payable|amount\s+payable)\s*[:=-]?\s*(?:(?:INR|Rs\.?|₹|USD|US\$|\$)\s*)?([\d,]+(?:\.\d{1,2})?)",
        text,
    )
    amount_due = None
    if amount_due_match:
        amount_due = amount_due_match.group(1).replace(",", "").strip()
        field_evidence["amount_due"] = amount_due_match.group(0).strip()

    # Service agreement parties: "Between Party A and Party B" or "Party A: ... Party B: ..."
    parties_match = re.search(
        r"(?im)^\s*(?:this\s+agreement\s+is\s+made\s+)?between\s+([^\n\r,]+?)\s+(?:and|&)\s+([^\n\r,.]+)",
        text,
    )
    contract_parties: list[str] = []
    if parties_match:
        p1 = parties_match.group(1).strip()
        p2 = parties_match.group(2).strip()
        if p1 and p2:
            contract_parties = [p1, p2]
            field_evidence["contract_parties"] = parties_match.group(0).strip()

    # Effective / Agreement date
    eff_match = re.search(
        r"(?im)^\s*(?:effective\s+date|agreement\s+date)\s*[:#-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
    )
    effective_date = None
    if eff_match:
        effective_date = eff_match.group(1).strip()
        field_evidence["effective_date"] = eff_match.group(0).strip()

    return {
        "emails": unique_emails,
        "phone_numbers": unique_phones,
        "dates": unique_dates,
        "text_length": len(text),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "amount_due": amount_due,
        "contract_parties": contract_parties,
        "effective_date": effective_date,
        "field_evidence": field_evidence,
    }
