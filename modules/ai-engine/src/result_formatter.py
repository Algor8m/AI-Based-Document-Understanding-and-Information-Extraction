
import json
from typing import Any


def format_result(
    document_id: str,
    extracted_facts: dict[str, Any],
    inferred_facts: dict[str, Any],
    fired_rules: list[dict[str, Any]],
    status: str = "success",
) -> dict[str, Any]:
    """Build a consistent, API-ready result."""

    return {
        "document_id": document_id,
        "status": status,
        "extracted_facts": extracted_facts,
        "inferred_facts": inferred_facts,
        "reasoning": fired_rules,
    }


def to_json(result: dict[str, Any]) -> str:
    """Serialize the result as readable JSON."""
    return json.dumps(result, indent=2, ensure_ascii=False)
