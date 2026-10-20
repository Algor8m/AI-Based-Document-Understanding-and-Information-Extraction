
import unittest

from src.document_classifier import classify_document
from src.analyzer import analyze_document


class TestDocumentClassifier(unittest.TestCase):

    def test_service_agreement(self):
        result = classify_document(
            "Service Agreement: Terms of Service"
        )
        self.assertEqual(
            result["document_type"],
            "service_agreement",
        )

    def test_invoice(self):
        result = classify_document(
            "Invoice Number: INV-101. Amount Due: 500"
        )
        self.assertEqual(result["document_type"], "invoice")

    def test_general_document(self):
        result = classify_document("Notes from the meeting")
        self.assertEqual(
            result["document_type"],
            "general_document",
        )

    def test_classifier_is_integrated_into_analyzer(self):
        result = analyze_document(
            "invoice-001",
            "Invoice Number: INV-101. Amount Due: 500",
        )

        self.assertEqual(
            result["classification"]["document_type"],
            "invoice",
        )
        self.assertEqual(
            result["inferred_facts"]["document_type"],
            "invoice",
        )


if __name__ == "__main__":
    unittest.main()
