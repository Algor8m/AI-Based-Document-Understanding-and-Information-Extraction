from pathlib import Path
import sys
import unittest

AI_ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_DIR))

from src.extractor import extract_facts
from src.knowledge_base import KnowledgeBase
from src.rule_engine import Rule, RuleEngine
from src.forward_chaining import ForwardChainer


class TestAIEngine(unittest.TestCase):

    def build_engine(self, text):
        extracted = extract_facts(text)

        kb = KnowledgeBase()
        kb.load_extracted_facts(extracted)
        kb.add_inferred_fact(
            "has_email",
            bool(kb.get_fact("emails", [])),
        )

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

        result = ForwardChainer(kb, engine).run()
        return extracted, result

    def test_email_is_extracted(self):
        extracted = extract_facts("Contact: ritam@example.com")
        self.assertIn("ritam@example.com", extracted["emails"])

    def test_missing_email_does_not_trigger_rules(self):
        _, result = self.build_engine(
            "This agreement describes the terms of service."
        )

        self.assertEqual(result["fired_rules"], [])
        self.assertFalse(result["inferred_facts"]["has_email"])
        self.assertNotIn(
            "contact_information_present",
            result["inferred_facts"],
        )

    def test_email_triggers_forward_chaining(self):
        _, result = self.build_engine(
            "Contact: ritam@example.com"
        )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(
            result["inferred_facts"]["contact_information_present"]
        )
        self.assertTrue(
            result["inferred_facts"]["has_contact_method"]
        )
        self.assertEqual(len(result["fired_rules"]), 2)


if __name__ == "__main__":
    unittest.main()
