
from typing import Any

from src.knowledge_base import KnowledgeBase
from src.rule_engine import RuleEngine


class ForwardChainer:
    """Apply rules until no new facts can be derived."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        rule_engine: RuleEngine,
    ):
        self.knowledge_base = knowledge_base
        self.rule_engine = rule_engine

    def run(self, max_iterations: int = 100) -> dict[str, Any]:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")

        fired_rules = []

        for iteration in range(1, max_iterations + 1):
            facts = self.knowledge_base.get_all_facts()
            results = self.rule_engine.evaluate_rules(facts)
            new_facts_added = False

            for result in results:
                conclusion = result["conclusion"]

                for key, value in conclusion.items():
                    if self.knowledge_base.add_inferred_fact(key, value):
                        fired_rules.append(result)
                        new_facts_added = True

            if not new_facts_added:
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "fired_rules": fired_rules,
                    "facts": self.knowledge_base.get_all_facts(),
                    "source_facts": self.knowledge_base.get_source_facts(),
                    "inferred_facts": self.knowledge_base.get_inferred_facts(),
                }

        return {
            "status": "iteration_limit_reached",
            "iterations": max_iterations,
            "fired_rules": fired_rules,
            "facts": self.knowledge_base.get_all_facts(),
            "source_facts": self.knowledge_base.get_source_facts(),
            "inferred_facts": self.knowledge_base.get_inferred_facts(),
        }
