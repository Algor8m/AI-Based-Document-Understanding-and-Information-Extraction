
from typing import Any


class KnowledgeBase:
    """Store source facts separately from inferred facts."""

    def __init__(self):
        self.facts: dict[str, Any] = {}
        self.source_facts: dict[str, Any] = {}
        self.inferred_facts: dict[str, Any] = {}

    def add_fact(self, key: str, value: Any) -> None:
        """Add or update a directly supplied fact."""
        self.facts[key] = value
        self.source_facts[key] = value
        self.inferred_facts.pop(key, None)

    def add_inferred_fact(self, key: str, value: Any) -> bool:
        """Add a derived fact if it is new or has changed."""
        if key in self.facts and self.facts[key] == value:
            return False

        self.facts[key] = value
        self.inferred_facts[key] = value
        return True

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)

    def has_fact(self, key: str) -> bool:
        return key in self.facts

    def get_all_facts(self) -> dict[str, Any]:
        return self.facts.copy()

    def get_source_facts(self) -> dict[str, Any]:
        return self.source_facts.copy()

    def get_inferred_facts(self) -> dict[str, Any]:
        return self.inferred_facts.copy()

    def load_extracted_facts(self, extracted: dict[str, Any]) -> None:
        """Load extractor output as source facts."""
        for key, value in extracted.items():
            self.add_fact(key, value)

    def clear(self) -> None:
        self.facts.clear()
        self.source_facts.clear()
        self.inferred_facts.clear()
