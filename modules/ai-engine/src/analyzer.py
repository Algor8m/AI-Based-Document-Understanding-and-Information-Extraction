"""Orchestration of entity extraction, classification, and rule-based reasoning."""

from typing import Any

from src.extractor import extract_facts
from src.document_classifier import classify_document
from src.knowledge_base import KnowledgeBase
from src.rule_engine import Rule, RuleEngine
from src.forward_chaining import ForwardChainer
from src.result_formatter import format_result


def analyze_document(
    document_id: str,
    text: str,
) -> dict[str, Any]:
    """Extract, classify, and reason about document text."""

    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("Document ID must not be empty.")

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Document text must not be empty.")

    # 1. Extract structured facts and field evidence
    extracted = extract_facts(text)
    field_evidence = extracted.get("field_evidence", {})

    # 2. Classify the document
    classification = classify_document(text)

    # 3. Initialize the knowledge base
    kb = KnowledgeBase()
    kb.load_extracted_facts(extracted)
    kb.add_inferred_fact(
        "document_type",
        classification["document_type"],
    )
    kb.add_inferred_fact(
        "has_email",
        bool(kb.get_fact("emails", [])),
    )

    # 4. Define reasoning rules
    engine = RuleEngine()

    engine.add_rule(
        Rule(
            name="EmailContactRule",
            conditions={"has_email": True},
            conclusion_key="contact_information_present",
            conclusion_value=True,
            description="The document contains an email address.",
        )
    )

    engine.add_rule(
        Rule(
            name="ContactMethodRule",
            conditions={"contact_information_present": True},
            conclusion_key="has_contact_method",
            conclusion_value=True,
            description="The document has a contact method.",
        )
    )

    # 5. Run forward chaining
    reasoning_result = ForwardChainer(kb, engine).run()

    # 6. Format the result including source evidence
    output = format_result(
        document_id=document_id,
        extracted_facts=reasoning_result["source_facts"],
        inferred_facts=reasoning_result["inferred_facts"],
        fired_rules=reasoning_result["fired_rules"],
        status=reasoning_result["status"],
        field_evidence=field_evidence,
    )

    # Include classification metadata in the response
    output["classification"] = classification

    return output
