
from typing import Any, Callable


class Rule:
    """Represent an IF-THEN rule."""

    def __init__(
        self,
        name: str,
        conditions: dict[str, Any],
        conclusion_key: str,
        conclusion_value: Any,
        description: str = "",
    ):
        self.name = name
        self.conditions = conditions
        self.conclusion_key = conclusion_key
        self.conclusion_value = conclusion_value
        self.description = description

    def evaluate(self, facts: dict[str, Any]) -> bool:
        """Return True when all conditions match."""
        return all(
            key in facts and facts[key] == expected
            for key, expected in self.conditions.items()
        )


class RuleEngine:
    """Evaluate rules against a collection of facts."""

    def __init__(self):
        self.rules: list[Rule] = []

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def evaluate_rules(
        self, facts: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Evaluate every rule and return triggered conclusions."""
        results = []

        for rule in self.rules:
            if rule.evaluate(facts):
                results.append({
                    "rule": rule.name,
                    "conclusion": {
                        rule.conclusion_key: rule.conclusion_value
                    },
                    "explanation": rule.description,
                })

        return results
