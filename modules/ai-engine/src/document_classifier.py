
import re


DOCUMENT_KEYWORDS = {
    "service_agreement": [
        "service agreement",
        "service contract",
        "contract for services",
        "contract of services",
        "terms of service",
        "scope of services",
        "scope of work",
        "service provider",
        "services between two parties",
    ],
    "invoice": [
        "invoice",
        "invoice number",
        "amount due",
        "bill to",
        "total payable",
    ],
}


def classify_document(text: str) -> dict[str, object]:
    """Classify a document using simple, explainable keyword matching."""

    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")

    normalized_text = re.sub(r"\s+", " ", text.lower()).strip()

    scores = {
        category: sum(
            1
            for keyword in keywords
            if keyword in normalized_text
        )
        for category, keywords in DOCUMENT_KEYWORDS.items()
    }

    best_category = max(scores, key=scores.get)

    if scores[best_category] == 0:
        return {
            "document_type": "general_document",
            "classification_method": "keyword_rules",
            "confidence": "low",
        }

    if list(scores.values()).count(scores[best_category]) > 1:
        return {
            "document_type": "general_document",
            "classification_method": "keyword_rules",
            "confidence": "low",
        }

    return {
        "document_type": best_category,
        "classification_method": "keyword_rules",
        "confidence": "medium",
    }
