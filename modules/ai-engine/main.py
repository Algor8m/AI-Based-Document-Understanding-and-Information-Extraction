
from src.extractor import extract_facts
from src.knowledge_base import KnowledgeBase
from src.rule_engine import Rule, RuleEngine
from src.forward_chaining import ForwardChainer
from src.result_formatter import format_result, to_json


def main():
    sample_text = """
    Document: Service Agreement
    Date: 2026-10-20
    This agreement describes the terms of service.
    """

    # Step 1: Extract facts from the document.
    extracted = extract_facts(sample_text)

    # Step 2: Initialize the knowledge base.
    kb = KnowledgeBase()
    kb.load_extracted_facts(extracted)

    # Step 3: Derive the email-presence fact.
    kb.add_inferred_fact(
        "has_email",
        bool(kb.get_fact("emails", [])),
    )

    # Step 4: Define the rules.
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

    # Step 5: Run forward chaining.
    result = ForwardChainer(kb, engine).run()

    # Step 6: Format the API-ready result.
    output = format_result(
        document_id="demo-document-001",
        extracted_facts=result["source_facts"],
        inferred_facts=result["inferred_facts"],
        fired_rules=result["fired_rules"],
        status=result["status"],
    )

    # Step 7: Display JSON output.
    print(to_json(output))


if __name__ == "__main__":
    main()
